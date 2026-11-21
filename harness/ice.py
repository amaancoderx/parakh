"""Parakh on IndicContextEval (AI4Bharat, Interspeech 2026): real Hindi speech with context lists.

    uv run python -I scripts/extract_ice.py <shard.parquet> data/external/ice_hi
    uv run python -m harness.ice --split dev
    uv run python -m harness.ice --split test      # final numbers only

The benchmark gives, for every utterance, a list of domain terms that may be spoken
and tags the English-origin terms in the reference. We use its English-script list
("L4"): its native-script list holds only about 2% of the rare tagged terms in our
subset, the English-script one about half. Every system gets the same audio; the
context-aware ones get the same list.

Scored here: tagged terms right (all, and the rare ones outside the 5,000 most common
Hindi and English words), list terms written but not spoken, and word error rate.
This is our scorer, not the benchmark's own (its scripts are not released yet), so the
numbers are comparable between rows of this table, not with the paper's.
"""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor

from harness.asr import transcribe
from harness.context import ContextIndex, common_word_keys
from harness.data import ROOT
from harness.parakh import Config, run
from harness.phonetic import key, skeleton
from harness.pronounce import pronunciations
from harness.score import aggregate, score_clip
from harness.systems import _cached, _sarvam

ICE_DIR = ROOT / "data" / "external" / "ice_hi"
RUNS_DIR = ROOT / "runs"
SCRIPT = (
    "Write the whole transcription in Devanagari (Hindi script). Transliterate spoken English "
    "words into Devanagari. Write numbers as words."
)
CFG = Config(name="Parakh", base="saaras-v4", witnesses=("saaras-v4", "saaras-v3", "gpt-transcribe"),
             languages=("hi",), prompt=SCRIPT, sarvam_mode="transcribe", sarvam_language="hi-IN", write_spoken=True)


def load(split: str) -> list[dict]:
    rows = [json.loads(line) for line in (ICE_DIR / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    return [{**r, "audio": ICE_DIR / "audio" / f"{r['id']}.wav"} for r in rows if split == "all" or r["split"] == split]


def usable(terms: list[str]) -> list[str]:
    """The benchmark's lists include fillers and everyday words ('umm', 'वो'); keep real terms only."""
    return [t for t in dict.fromkeys(terms) if len(skeleton(t)) >= 2 and key(t) not in common_word_keys()]


WITNESSES = {
    "saaras-v4": _cached("ice saaras-v4 transcribe", _sarvam("saaras:v4", "transcribe", language="hi-IN")),
    "saaras-v3": _cached("ice saaras-v3 transcribe", _sarvam("saaras:v3", "transcribe", language="hi-IN")),
    "gpt-transcribe": lambda audio: transcribe(audio, "gpt-transcribe", languages=["hi"], prompt=SCRIPT),
}


NO_CONTEXT = False


def transcripts(row: dict) -> dict[str, dict]:
    """Every system's output for one utterance."""
    audio, terms = row["audio"], usable(row["l4"])
    out = {name: fn(audio) for name, fn in WITNESSES.items()}
    if NO_CONTEXT:
        out["Parakh"] = run(audio, ContextIndex({}, None), CFG, WITNESSES)
        return out
    if terms:
        out["gpt-transcribe + its keyword list"] = transcribe(
            audio, "gpt-transcribe", languages=["hi"], prompt=SCRIPT, keywords=terms)
        out["saaras-v4 + its keyword list"] = _cached(
            "ice saaras-v4 kt " + "|".join(terms), _sarvam("saaras:v4", "transcribe", terms, language="hi-IN"))(audio)
        index = ContextIndex.build({"brands": terms})  # pronunciations were fetched for the whole run in main()
        out["Parakh"] = run(audio, index, CFG, WITNESSES)
    else:  # no usable context for this utterance: the context-aware systems fall back to their base
        out["gpt-transcribe + its keyword list"] = out["gpt-transcribe"]
        out["saaras-v4 + its keyword list"] = out["saaras-v4"]
        out["Parakh"] = out["saaras-v4"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--limit", type=int, default=0, help="first N utterances only")
    ap.add_argument("--no-context", action="store_true", help="give no system a term list: recognisers alone")
    args = ap.parse_args()
    global NO_CONTEXT
    NO_CONTEXT = args.no_context
    rows = load(args.split)[: args.limit or None]
    if not rows:
        raise SystemExit("No utterances. Run scripts/extract_ice.py first.")

    pronunciations(sorted({t for r in rows for t in usable(r["l4"])}))  # one batch, cached on disk
    with ThreadPoolExecutor(max_workers=3) as pool:  # Sarvam calls are throttled inside the adapter
        outputs = list(pool.map(transcripts, rows))

    scored: dict[str, list[dict]] = {}
    for row, outs in zip(rows, outputs):
        terms = usable(row["l4"])
        rare = [t for t in row["terms"] if key(t[0]) not in common_word_keys()]
        for name, o in outs.items():
            text = o["text"].replace("\n", " ")
            s = score_clip(row["ref"], text, row["terms"], [], terms)
            s["rare_hits"] = [h for t, h in zip(row["terms"], s["entity_hits"]) if t in rare]
            s.update(id=row["id"], hyp=text, latency_s=o.get("latency_s"))
            scored.setdefault(name, []).append(s)

    def pct(x):
        return "n/a" if x is None else f"{100 * x:.1f}%"

    table = ["| System | Tagged terms right | Rare terms right | List terms written but not said | WER |", "|---|---|---|---|---|"]
    summary = {}
    for name, ss in scored.items():
        a = aggregate(ss)
        rare = [h for s in ss for h in s["rare_hits"]]
        summary[name] = {**a, "rare_acc": sum(rare) / len(rare) if rare else None, "rare_n": len(rare)}
    for name in sorted(summary, key=lambda n: -(summary[n]["rare_acc"] or 0)):
        a = summary[name]
        table.append(f"| {name} | {pct(a['entity_acc'])} | {pct(a['rare_acc'])} | {a['false_insertions']} | {pct(a['wer'])} |")
    any_row = next(iter(summary.values()))
    minutes = sum(r["duration"] for r in rows) / 60
    head = ("No context given to any system. " if args.no_context else "") + (
            f"IndicContextEval Hindi, {args.split} split: {len(rows)} utterances, {minutes:.1f} min, "
            f"{len({r['speaker'] for r in rows})} speakers, {any_row['entity_n']} tagged terms ({any_row['rare_n']} rare)")
    stem = f"ice-{args.split}" + ("-nocontext" if args.no_context else "")
    print(f"\n{head}\n\n" + "\n".join(table))
    RUNS_DIR.mkdir(exist_ok=True)
    (RUNS_DIR / f"{stem}.md").write_text(head + "\n\n" + "\n".join(table) + "\n", encoding="utf-8")
    (RUNS_DIR / f"{stem}.json").write_text(
        json.dumps({"summary": summary, "clips": scored}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
