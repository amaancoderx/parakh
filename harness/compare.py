"""Comparison table: the same recordings through every system.

    uv run python -m harness.compare                    # real recordings, dev split
    uv run python -m harness.compare --audio synth --split all
    uv run python -m harness.compare --split test       # final numbers only
    uv run python -m harness.compare --systems "gpt-transcribe" "saaras-v3 translit"

Systems with no API (e.g. another product's app) can still be scored: put their
transcripts in runs/external/<system name>.jsonl, one {"id": ..., "text": ...}
per line, and they appear in the table.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness.data import AUDIO_DIR, ROOT, Clip, load_manifest
from harness.score import aggregate, score_clip
from harness.parakh import parakh_systems
from harness.systems import SystemFn, available_systems, context_terms

RUNS_DIR = ROOT / "runs"
EXTERNAL_DIR = RUNS_DIR / "external"
AUDIO_DIRS = {"real": AUDIO_DIR, "synth": ROOT / "data" / "audio_synth"}


def external_systems(directory: Path = EXTERNAL_DIR) -> dict[str, dict[str, str]]:
    """name -> {clip id -> transcript}, read from <directory>/*.jsonl."""
    out = {}
    for path in sorted(directory.glob("*.jsonl")) if directory.exists() else []:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        out[path.stem] = {r["id"]: r["text"] for r in rows}
    return out


def score_system(clips: list[Clip], texts: dict[str, dict], terms: list[str] | None = None) -> dict:
    """texts: clip id -> {"text", "latency_s"?}. Scores the clips this system covered."""
    rows = []
    for c in clips:
        if c.id not in texts:
            continue
        row = score_clip(c.ref, texts[c.id]["text"], c.entities, c.formats, terms)
        row.update(id=c.id, ref=c.ref, hyp=texts[c.id]["text"], tags=c.tags, latency_s=texts[c.id].get("latency_s"))
        rows.append(row)
    agg = aggregate(rows)
    lat = [r["latency_s"] for r in rows if r["latency_s"] is not None]
    agg["mean_latency_s"] = sum(lat) / len(lat) if lat else None
    traps = [r for r in rows if any(t.startswith("trap") for t in r["tags"])]
    agg["trap_entity_acc"] = aggregate(traps)["entity_acc"] if traps else None
    return {"aggregate": agg, "clips": rows}


def run_api_system(fn: SystemFn, clips: list[Clip], workers: int = 1) -> dict[str, dict]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda c: fn(c.audio), clips))
    return {c.id: r for c, r in zip(clips, results)}


def markdown_table(results: dict[str, dict], total_clips: int) -> str:
    def pct(x):
        return "n/a" if x is None else f"{100 * x:.1f}%"

    # Best first: highest entity accuracy, then fewest wrong names, then lowest WER.
    order = sorted(
        results,
        key=lambda n: (
            -(results[n]["aggregate"]["entity_acc"] or 0),
            results[n]["aggregate"]["false_insertions"],
            results[n]["aggregate"]["wer"] or 9,
        ),
    )
    lines = [
        "| System | Names right | Trap names right | Wrong names inserted | Numbers right | WER | Latency | Clips |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in order:
        a = results[name]["aggregate"]
        lat = "n/a" if a["mean_latency_s"] is None else f"{a['mean_latency_s']:.2f}s"
        partial = "" if a["clips"] == total_clips else " (partial)"
        lines.append(
            f"| {name} | {pct(a['entity_acc'])} | {pct(a['trap_entity_acc'])} | {a['false_insertions']} "
            f"| {pct(a['format_acc'])} | {pct(a['wer'])} | {lat} | {a['clips']}/{total_clips}{partial} |"
        )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--audio", default="real", choices=list(AUDIO_DIRS), help="synth = TTS dev clips, not evidence")
    ap.add_argument("--systems", nargs="*", help="subset of system names; default is all available")
    args = ap.parse_args()

    if args.split == "test" and args.audio == "real":
        print("NOTE: test split is frozen. Use it for final numbers only, not for tuning.")
    clips = load_manifest(split=None if args.split == "all" else args.split, audio_dir=AUDIO_DIRS[args.audio])
    clips = [c for c in clips if c.audio]
    if not clips:
        raise SystemExit("No audio found. Record with: uv run python -m harness.record")

    api = {**available_systems(), **parakh_systems()}
    external = external_systems() if args.audio == "real" else {}
    names = args.systems or [*api, *external]
    unknown = [n for n in names if n not in api and n not in external]
    if unknown:
        raise SystemExit(f"Unknown systems: {unknown}. Available: {[*api, *external]}")

    terms = context_terms()
    results = {}
    for name in names:
        print(f"running {name} ...")
        try:
            if name in api:
                # Sarvam and ElevenLabs are rate limited on their entry tiers; keep them serial.
                texts = run_api_system(api[name], clips, workers=4 if name.startswith("gpt") else 1)
            else:
                texts = {cid: {"text": t} for cid, t in external[name].items()}
            results[name] = score_system(clips, texts, terms)
        except Exception as e:  # one broken provider must not sink the whole table
            print(f"  FAILED, left out of the table: {type(e).__name__}: {e}")
    if not results:
        raise SystemExit("No system produced results.")

    table = markdown_table(results, len(clips))
    label = f"{args.audio} audio, {args.split} split, {len(clips)} clips"
    print(f"\n{label}\n\n{table}\n")
    if any(r["aggregate"]["clips"] != len(clips) for r in results.values()):
        print("Rows marked (partial) were scored on fewer clips and are not directly comparable.\n")

    RUNS_DIR.mkdir(exist_ok=True)
    stem = f"compare-{args.audio}-{args.split}"
    (RUNS_DIR / f"{stem}.md").write_text(f"{label}\n\n{table}\n", encoding="utf-8")
    (RUNS_DIR / f"{stem}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved runs/{stem}.md and .json")


if __name__ == "__main__":
    main()
