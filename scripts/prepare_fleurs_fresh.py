"""Prepare the FLEURS Hindi TEST split as a second, untouched names test.

    # test.tar.gz and test.tsv (hi_in) from huggingface.co/datasets/google/fleurs go in data/external/fleurs_hi_fresh/
    uv run python scripts/prepare_fleurs_fresh.py

Same recipe as scripts/prepare_fleurs.py: an OpenAI model tags the proper names in each
reference sentence, and the context list is every name in the set. Nothing was tuned on
these recordings: the rules were frozen before the first run on them. No sentence here
appears in the other set.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prepare_fleurs import tag  # noqa: E402

DIR = Path(__file__).resolve().parent.parent / "data" / "external" / "fleurs_hi_fresh"


def main() -> None:
    rows = []
    with (DIR / "test.tsv").open(encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            rows.append({"sentence": r[0], "file": r[1], "raw": r[2]})
    names_file = DIR / "names.json"
    if names_file.exists():
        names = json.loads(names_file.read_text(encoding="utf-8"))
    else:
        names = tag(list({r["sentence"]: r["raw"] for r in rows}.items()))
        names_file.write_text(json.dumps(names, ensure_ascii=False, indent=1), encoding="utf-8")
    (DIR / "wav16").mkdir(exist_ok=True)
    manifest = []
    for r in rows:
        ns, src = names.get(r["sentence"], []), DIR / "test" / r["file"]
        if not ns or not src.exists():
            continue
        out = DIR / "wav16" / r["file"]  # 16-bit copies: FLEURS ships float wavs
        if not out.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(out)], check=True)
        manifest.append({"id": Path(r["file"]).stem, "sentence": r["sentence"], "ref": r["raw"], "names": ns, "split": "fresh"})
    with (DIR / "manifest.jsonl").open("w", encoding="utf-8") as f:
        for m in manifest:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    all_names = sorted({n for m in manifest for n in m["names"]})
    (DIR / "context.json").write_text(json.dumps({"brands": all_names}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} recordings, {len(manifest)} with a name; {sum(len(m['names']) for m in manifest)} name mentions; "
          f"{len(all_names)} distinct names in the context list; {len({m['sentence'] for m in manifest})} distinct sentences")
    for m in manifest[:4]:
        print("  ", m["names"], "|", m["ref"][:90])


if __name__ == "__main__":
    main()
