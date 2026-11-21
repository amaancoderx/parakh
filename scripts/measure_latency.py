"""Wall-clock latency of POST /speech-to-text on audio the service has never seen.

    uv run python scripts/measure_latency.py            # the service must be running on :8000

Takes segments of the three real calls (with each call's name list) and public FLEURS
recordings (with the 100-name list), adds 10 ms of silence to each so that no saved
recogniser response can be replayed, and sends them one at a time as a stream. Records,
on the client, when the draft line and the checked line arrive.

Costs real recogniser calls: about three per clip.
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
URL = "http://localhost:8000/speech-to-text"
OUT = ROOT / "runs" / "latency.json"
FRESH = ROOT / "data" / "uploads" / "latency"
PAD = 0.03  # seconds of silence added; change it to measure again, or the last run's answers are replayed


def clips(n_public: int) -> list[tuple[Path, list[str], str]]:
    out = []
    for call in ("dad_call", "call2", "call3"):
        own = ROOT / "data" / "real" / call / "context.json"  # the call-back shares the list of the call before it
        ctx = json.loads((own if own.exists() else ROOT / "data" / "real" / "call2" / "context.json").read_text(encoding="utf-8"))
        names = [n for k in ("contacts", "places", "brands") for n in ctx.get(k, [])]
        out += [(seg, names, "call") for seg in sorted((ROOT / "data" / "samples" / call / "segments").glob("seg*.wav"))]
    fleurs = ROOT / "data" / "external" / "fleurs_hi"
    names = json.loads((fleurs / "context.json").read_text(encoding="utf-8"))["brands"]
    rows = [json.loads(line) for line in (fleurs / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    test = [r for r in rows if r["split"] == "test"][:n_public]
    return out + [(fleurs / "wav16" / f"{r['id']}.wav", names, "public") for r in test]


def fresh(audio: Path, n: int, pad: float = 0) -> Path:
    """The same audio with a little silence added: new bytes, so nothing saved can be replayed."""
    FRESH.mkdir(parents=True, exist_ok=True)
    out = FRESH / f"{n:03d}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(audio), "-af", f"apad=pad_dur={pad or PAD}",
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(out)], check=True)
    return out


def seconds(wav: Path) -> float:
    import wave
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, round(q * (len(xs) - 1)))]


def example() -> dict:
    """The request shown on the page, for real: the 'Aishar' clip with two names, never seen before."""
    wav = fresh(ROOT / "data" / "samples" / "dad_call" / "segments" / "seg04.wav", 900, PAD + 0.013)  # not the main loop's copy
    t0, marks, final = time.perf_counter(), {}, None
    with httpx.stream("POST", URL, files={"file": (wav.name, wav.read_bytes(), "audio/wav")},
                      data={"names": "Eicher, Mohammad bhai", "stream": "true"}, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line.strip():
                final = json.loads(line)
                marks[final["event"]] = round(1000 * (time.perf_counter() - t0))
    p = final["parakh"]
    return {"draft_ms": marks["draft"], "verified_ms": marks["verified"], "extra_listens": p["extra_listens"],
            "edits": [[e["from"], e["to"]] for e in p["edits"]], "replayed": p["replayed"]}


def main() -> None:
    n_public = int(sys.argv[1]) if len(sys.argv) > 1 else 23
    rows = []
    for n, (audio, names, kind) in enumerate(clips(n_public)):
        wav = fresh(audio, n)
        t0 = time.perf_counter()
        marks, final = {}, None
        with httpx.stream("POST", URL, files={"file": (wav.name, wav.read_bytes(), "audio/wav")},
                          data={"names": ", ".join(names), "stream": "true"}, timeout=120) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line.strip():
                    step = json.loads(line)
                    marks[step["event"]] = round(1000 * (time.perf_counter() - t0))
                    final = step
        p = final["parakh"]
        rows.append({"kind": kind, "seconds": round(seconds(wav), 1), "draft_ms": marks["draft"], "verified_ms": marks["verified"],
                     "extra_listens": p["extra_listens"], "edits": len(p["edits"]), "replayed": p["replayed"],
                     "recognisers_ms": p["timing_ms"]["recognisers"], "left_out": p["left_out"]})
        print(f"{n:3d} {kind:6} {rows[-1]['seconds']:5.1f}s  draft {marks['draft']:5d} ms  checked {marks['verified']:5d} ms  "
              f"extra listens {p['extra_listens']}  edits {len(p['edits'])}  {p['timing_ms']['recognisers']}", flush=True)
        time.sleep(1.2)  # stay well inside Sarvam's 60 requests a minute
    live = [r for r in rows if not r["replayed"]]
    plain = [r for r in live if not r["extra_listens"]]
    more = [r for r in live if r["extra_listens"]]
    summary = {
        "clips": len(live), "median_seconds": statistics.median(r["seconds"] for r in live),
        "draft_ms": {"median": statistics.median(r["draft_ms"] for r in live), "p90": pct([r["draft_ms"] for r in live], 0.9)},
        "verified_ms": {"median": statistics.median(r["verified_ms"] for r in live), "p90": pct([r["verified_ms"] for r in live], 0.9)},
        "added_ms": {"median": statistics.median(r["verified_ms"] - r["draft_ms"] for r in live),
                     "p90": pct([r["verified_ms"] - r["draft_ms"] for r in live], 0.9)},
        "no_extra_listen": {"clips": len(plain), "verified_ms_median": statistics.median(r["verified_ms"] for r in plain) if plain else None},
        "extra_listen": {"clips": len(more), "verified_ms_median": statistics.median(r["verified_ms"] for r in more) if more else None},
        "recognisers_ms_median": {w: statistics.median(r["recognisers_ms"][w] for r in live if w in r["recognisers_ms"])
                                  for w in sorted({w for r in live for w in r["recognisers_ms"]})},
        # per layer: all three heard; the check alone (no second listen); the second listen and its check
        "all_heard_ms": {"median": statistics.median(max(r["recognisers_ms"].values()) for r in live)},
        "check_ms": {"median": statistics.median(r["verified_ms"] - max(r["recognisers_ms"].values()) for r in plain) if plain else None},
        "hear_again_ms": {"median": statistics.median(r["verified_ms"] - max(r["recognisers_ms"].values()) for r in more) if more else None},
        "example": example(),
    }
    OUT.write_text(json.dumps({"summary": summary, "clips": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
