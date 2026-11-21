"""Base run: transcribe every recorded clip with a stock model and print the error breakdown.

    uv run python -m harness.run_base
    uv run python -m harness.run_base --model gpt-4o-transcribe --name old
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

from harness.asr import transcribe
from harness.data import ROOT, load_manifest
from harness.score import CATEGORIES, aggregate, score_clip

RUNS_DIR = ROOT / "runs"


def pct(x: float | None) -> str:
    return "   n/a" if x is None else f"{100 * x:5.1f}%"


def print_report(agg: dict, rows: list[dict], worst: int) -> None:
    print(f"\nclips {agg['clips']}   ref tokens {agg['ref_tokens']}")
    print(f"WER              {pct(agg['wer'])}")
    print(f"entity accuracy  {pct(agg['entity_acc'])}  (n={agg['entity_n']})")
    print(f"format accuracy  {pct(agg['format_acc'])}  (n={agg['format_n']})")
    print(f"non-Latin output {pct(agg['non_latin_share'])}  (refs are Roman script; high = script mismatch)")
    lat = [r["latency_s"] for r in rows]
    print(f"mean latency     {sum(lat) / len(lat):5.2f}s")

    print("\nerrors by type        count   rate within type")
    for c in CATEGORIES:
        print(f"  {c:<18} {agg['errors_by_cat'][c]:>6}   {pct(agg['error_rate_by_cat'][c])}")
    print(f"  {'insertion':<18} {agg['errors_by_cat']['insertion']:>6}")
    print("  (format errors include valid digit renderings; format accuracy is the fair number)")

    by_tag = defaultdict(list)
    for r in rows:
        for tag in r["tags"]:
            by_tag[tag].append(r)
    print("\nby tag             clips    WER   entity   format")
    for tag in sorted(by_tag):
        a = aggregate(by_tag[tag])
        print(f"  {tag:<16} {a['clips']:>5} {pct(a['wer'])}  {pct(a['entity_acc'])}  {pct(a['format_acc'])}")

    print(f"\nworst {worst} clips")
    for r in sorted(rows, key=lambda r: -r["wer"])[:worst]:
        print(f"  {r['id']}  WER {pct(r['wer'])}")
        print(f"    ref: {r['ref']}")
        print(f"    hyp: {r['hyp']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-transcribe")
    ap.add_argument("--language", default=None, help="ISO code hint, e.g. en or hi")
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--name", default=None, help="run name; defaults to base-<model>-<split>")
    ap.add_argument("--worst", type=int, default=8)
    args = ap.parse_args()

    if args.split == "test":
        print("NOTE: test split is frozen. Use it for final numbers only, not for tuning.")

    clips = load_manifest(split=None if args.split == "all" else args.split)
    recorded = [c for c in clips if c.audio]
    missing = [c.id for c in clips if not c.audio]
    if missing:
        print(f"{len(missing)} clips have no audio yet: {' '.join(missing)}")
    if not recorded:
        raise SystemExit("No audio found in data/audio/. Record with: uv run python -m harness.record")

    rows = []
    for c in recorded:
        res = transcribe(c.audio, args.model, language=args.language, prompt=args.prompt)
        row = score_clip(c.ref, res["text"], c.entities, c.formats)
        row.update(id=c.id, ref=c.ref, hyp=res["text"], tags=c.tags, latency_s=res["latency_s"])
        rows.append(row)
        print(f"  {c.id}  WER {pct(row['wer'])}{'  (cached)' if res['cached'] else ''}")

    agg = aggregate(rows)
    print_report(agg, rows, args.worst)

    name = args.name or f"base-{args.model}-{args.split}"
    RUNS_DIR.mkdir(exist_ok=True)
    out = RUNS_DIR / f"{name}.json"
    config = {"model": args.model, "language": args.language, "prompt": args.prompt, "split": args.split}
    out.write_text(
        json.dumps({"config": config, "aggregate": agg, "clips": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nsaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
