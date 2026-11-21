"""Prepare the open FLEURS Hindi dev set (Google, CC BY 4.0) as a names test.

    uv run python scripts/prepare_fleurs.py

FLEURS has no entity labels, so an OpenAI model tags the proper names in each
REFERENCE sentence (people, places, organisations, products), exactly as written.
The tags are saved to data/external/fleurs_hi/names.json for review. The context
given to every context-aware system is the list of ALL names in the set, so each
utterance sees its own names among a few hundred others: the standard biasing-list
protocol, and close to a real phone book.

Sentences are split dev/test by a hash of the sentence id, so the same sentence read
by two speakers never lands on both sides.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.asr import client  # noqa: E402

DIR = Path(__file__).resolve().parent.parent / "data" / "external" / "fleurs_hi"
PROMPT = (
    "Each line is 'id<TAB>Hindi sentence'. For each sentence list the proper names in it: people, places, "
    "organisations, brands, named events and works. Copy each name exactly as written in the sentence "
    "(Devanagari, same spelling, full multi-word name as one item). No common nouns, no languages or "
    "nationalities used as adjectives, no dates or numbers. Reply with only JSON: {id: [names]} for every id."
)


def tag(rows: list[tuple[str, str]], batch: int = 50) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        body = "\n".join(f"{rid}\t{text}" for rid, text in chunk)
        resp = client().chat.completions.create(
            model="gpt-5.5", reasoning_effort="low",
            messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": body}],
            response_format={"type": "json_object"},
        )
        got = json.loads(resp.choices[0].message.content or "{}")
        for rid, text in chunk:
            out[rid] = [n for n in got.get(rid, []) if isinstance(n, str) and n in text]
        print(f"tagged {min(i + batch, len(rows))}/{len(rows)}", flush=True)
    return out


def main() -> None:
    rows = []
    with (DIR / "dev.tsv").open(encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            rows.append({"sentence": r[0], "file": r[1], "ref": r[3] if len(r) > 3 and r[3] else r[2], "raw": r[2]})
    names_file = DIR / "names.json"
    if names_file.exists():
        names = json.loads(names_file.read_text(encoding="utf-8"))
    else:
        unique = list({r["sentence"]: r["raw"] for r in rows}.items())
        names = tag(unique)
        names_file.write_text(json.dumps(names, ensure_ascii=False, indent=1), encoding="utf-8")
    manifest = []
    for r in rows:
        ns = names.get(r["sentence"], [])
        if not ns or not (DIR / "dev" / r["file"]).exists():
            continue
        manifest.append({
            "id": Path(r["file"]).stem, "sentence": r["sentence"], "ref": r["raw"], "names": ns,
            "split": "dev" if hashlib.sha1(r["sentence"].encode()).digest()[0] % 10 < 3 else "test",
        })
    with (DIR / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    all_names = sorted({n for m in manifest for n in m["names"]})
    (DIR / "context.json").write_text(json.dumps({"brands": all_names}, ensure_ascii=False, indent=1), encoding="utf-8")
    dev = sum(m["split"] == "dev" for m in manifest)
    print(f"{len(rows)} utterances, {len(manifest)} with a name; dev {dev} / test {len(manifest) - dev}; "
          f"{sum(len(m['names']) for m in manifest)} name mentions; {len(all_names)} distinct names in the context list")
    for m in manifest[:5]:
        print("  ", m["names"], "|", m["ref"][:90])


if __name__ == "__main__":
    main()
