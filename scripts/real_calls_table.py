"""Scoreboard on the real call recordings, for the words a person has confirmed.

    uv run python scripts/real_calls_table.py

data/real/truth.json lists, per call, the confirmed names and numbers and how many
times each is said. A mention counts as right when the system wrote the saved
spelling, or the same sound in Hindi script. "Wrong names" counts context names
that were written but never said.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.asr import transcribe  # noqa: E402
from harness.context import ContextIndex  # noqa: E402
from harness.parakh import Config, run  # noqa: E402
from harness.phonetic import key, same_sound  # noqa: E402
from harness.score import normalize, tokens  # noqa: E402
from harness.systems import _cached, _sarvam, available_systems  # noqa: E402

REAL = Path(__file__).resolve().parent.parent / "data" / "real"


def count(text: str, variants: list[str], strict: bool = False) -> int:
    """How many times any variant appears: exact for Roman script, same sound for Devanagari words.

    strict=True (used for wrong names) needs a Devanagari word to have exactly the
    variant's sound key, so that an everyday word like अंदर is not read as "Indore".
    """
    toks = tokens(text)
    used, n = set(), 0
    for size in sorted({len(normalize(v).split()) for v in variants}, reverse=True):
        for i in range(len(toks) - size + 1):
            if not used.isdisjoint(range(i, i + size)):
                continue
            window = toks[i : i + size]
            joined = " ".join(t for t, _ in window)
            hit = any(joined == normalize(v) for v in variants)
            if not hit and any(dev for _, dev in window):
                if strict:
                    hit = any(key(joined) == key(v) for v in variants)
                else:
                    hit = any(same_sound(joined, v, strict_final=True) for v in variants)
            if hit:
                n += 1
                used.update(range(i, i + size))
    return n


def table() -> tuple[int, int, dict[str, dict[str, int]]]:
    """(confirmed mentions, calls, {system: {"right", "wrong"}})."""
    truth = json.loads((REAL / "truth.json").read_text(encoding="utf-8"))
    base = available_systems()
    totals: dict[str, dict[str, int]] = {}
    said_total = 0
    for call, spec in truth.items():
        ctx_path = REAL / spec["context"] / "context.json"
        index = ContextIndex.load(ctx_path)
        ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
        terms = [t for f in ("contacts", "places", "brands") for t in ctx.get(f, [])]
        systems = {
            "Saaras v3": base["saaras-v3 translit"],
            "Saaras v4": base["saaras-v4 translit"],
            "gpt-transcribe": base["gpt-transcribe + hi/en"],
            "Saaras v4 + its keyword list": _cached("saaras-v4 translit kt " + "|".join(terms), _sarvam("saaras:v4", "translit", terms)),
            "gpt-transcribe + its keyword list": lambda a, terms=terms: transcribe(a, "gpt-transcribe", keywords=terms, languages=["hi", "en"]),
            "Parakh": lambda a, index=index: run(a, index, Config(), base),
        }
        segs = sorted((REAL / call / "segments").glob("seg*.wav"))
        confirmed = spec["entities"] + spec.get("numbers", [])
        said_total += sum(e["count"] for e in confirmed)
        confirmed_names = {e["name"] for e in spec["entities"]}
        for name, fn in systems.items():
            text = " ".join(fn(s)["text"].replace("\n", " ") for s in segs)
            row = totals.setdefault(name, {"right": 0, "wrong": 0})
            for e in confirmed:
                variants = [e["name"], *e.get("variants", []), *index.by_text.get(e["name"], type("x", (), {"spoken": ()})).spoken]
                row["right"] += min(count(text, variants), e["count"])
            for t in terms:
                if t not in confirmed_names and t not in spec.get("unconfirmed", []):
                    row["wrong"] += count(text, [t, *index.by_text[t].spoken], strict=True)
    return said_total, len(truth), totals


def table_no_context() -> tuple[int, dict[str, int]]:
    """Confirmed words right when nothing is typed in and nothing is remembered."""
    from harness import memory
    from harness.call import process_call

    truth = json.loads((REAL / "truth.json").read_text(encoding="utf-8"))
    base = available_systems()
    empty = ContextIndex({}, None)
    spoken = {"Eicher": ["आइशर"], "Arizona Bianco": ["एरिज़ोना बियांको"], "Mohammad bhai": ["मोहम्मद भाई"]}
    totals: dict[str, int] = {}
    said = 0
    for call, spec in truth.items():
        segs = sorted((REAL / call / "segments").glob("seg*.wav"))
        confirmed = spec["entities"] + spec.get("numbers", [])
        said += sum(e["count"] for e in confirmed)
        memory.forget("no-context-eval")
        texts = {
            "Saaras v3": " ".join(base["saaras-v3 translit"](s)["text"].replace("\n", " ") for s in segs),
            "Saaras v4": " ".join(base["saaras-v4 translit"](s)["text"].replace("\n", " ") for s in segs),
            "gpt-transcribe": " ".join(base["gpt-transcribe + hi/en"](s)["text"].replace("\n", " ") for s in segs),
            "Parakh, recognisers only": " ".join(run(s, empty, Config(), base)["text"].replace("\n", " ") for s in segs),
            "Parakh, with its own topic search": " ".join(x["text"] for x in process_call(None, call, user="no-context-eval")["segments"]),
        }
        memory.forget("no-context-eval")
        for name, text in texts.items():
            for e in confirmed:
                variants = [e["name"], *e.get("variants", []), *spoken.get(e["name"], [])]
                totals[name] = totals.get(name, 0) + min(count(text, variants), e["count"])
    return said, totals


def main() -> None:
    said_total, calls, totals = table()
    print(f"{said_total} confirmed mentions across {calls} calls\n")
    print("| System | Confirmed words right | Wrong names written |")
    print("|---|---|---|")
    for name, row in sorted(totals.items(), key=lambda kv: (-kv[1]["right"], kv[1]["wrong"])):
        print(f"| {name} | {row['right']} of {said_total} | {row['wrong']} |")


if __name__ == "__main__":
    main()
