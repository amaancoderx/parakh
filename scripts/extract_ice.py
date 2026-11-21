"""Extract a test subset from an IndicContextEval parquet shard (AI4Bharat, CC BY 4.0).

    uv run python -I scripts/extract_ice.py <shard.parquet> <out_dir> [--n 200] [--per-speaker 6]

Standalone on purpose (no project imports): it reads a downloaded file. Writes
<out_dir>/audio/<id>.wav and <out_dir>/manifest.jsonl with, per utterance, the
reference, the tagged English-origin terms, and the benchmark's own context lists
(L4 English script, L5 native script, L6 wrong-domain list).

Kept: 2-28 s clips (Sarvam's REST API takes under 30 s) with at least one tagged term.
Speakers are split dev/test by a hash of the speaker id, so no speaker is in both.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pyarrow.parquet as pq

TAGGED = re.compile(r"\(([A-Za-z][A-Za-z0-9 .'\-]*)\)")
ANGLE = re.compile(r"<[^>]*>")


def tagged_terms(text: str) -> list[list[str]]:
    """'सेन्स (sense) डेटा (data)' -> [['सेन्स', 'sense'], ['डेटा', 'data']]."""
    text = ANGLE.sub(" ", text)
    out = []
    for m in TAGGED.finditer(text):
        english = m.group(1).strip()
        before = text[: m.start()].split()
        before = [w for w in before if not w.startswith("(") and not w.endswith(")")]
        k = max(1, len(english.split()))
        native = " ".join(before[-k:])
        if native and re.search(r"[ऀ-ॿ]", native):
            out.append([native, english])
    return out


def context_list(prompt: str) -> list[str]:
    """The comma-separated list on the line after the prompt's first ':'."""
    head, _, rest = prompt.partition(":\n")
    if not rest:
        return []
    return [t.strip() for t in rest.split("\n", 1)[0].split(",") if t.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("parquet", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--per-speaker", type=int, default=6)
    args = ap.parse_args()

    (args.out_dir / "audio").mkdir(parents=True, exist_ok=True)
    pf = pq.ParquetFile(args.parquet)
    per_speaker: dict[str, int] = {}
    rows = []
    for g in range(pf.metadata.num_row_groups):
        for r in pf.read_row_group(g).to_pylist():
            if len(rows) >= args.n:
                break
            terms = tagged_terms(r["reference_text_with_tags"])
            ref = " ".join(ANGLE.sub(" ", r["reference_text_no_tags"]).split())
            if not terms or not ref or not 2.0 <= r["duration"] <= 28.0:
                continue
            spk = str(r["speaker_id"])
            if per_speaker.get(spk, 0) >= args.per_speaker:
                continue
            per_speaker[spk] = per_speaker.get(spk, 0) + 1
            clip_id = Path(r["file_name"]).stem
            (args.out_dir / "audio" / f"{clip_id}.wav").write_bytes(r["audio"]["bytes"])
            rows.append({
                "id": clip_id,
                "ref": ref,
                "terms": terms,
                "l4": context_list(r["l4_prompt"]),
                "l5": context_list(r["l5_prompt"]),
                "l6": context_list(r["l6_prompt"]),
                "speaker": spk,
                "split": "dev" if hashlib.sha1(spk.encode()).digest()[0] % 10 < 3 else "test",
                "duration": r["duration"],
                "code_mixing": r["code_mixing"],
                "style": r["speech_style"],
                "domain": r["domain_name"],
            })
    with (args.out_dir / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    minutes = sum(r["duration"] for r in rows) / 60
    dev = sum(r["split"] == "dev" for r in rows)
    print(f"{len(rows)} clips, {minutes:.1f} min, {len(per_speaker)} speakers, dev {dev} / test {len(rows) - dev}")
    print(f"{sum(len(r['terms']) for r in rows)} tagged terms")


if __name__ == "__main__":
    main()
