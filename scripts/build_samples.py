"""Bundle the demo recordings under data/samples/ (git-ignored: these are private calls).

    uv run python scripts/build_samples.py

Copies each real call's recording and the exact segment files the cache was built from,
so the demo replays them without new API calls.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REAL, OUT = ROOT / "data" / "real", ROOT / "data" / "samples"
CALLS = [
    ("dad_call", "Call 1 · Steel drums order", "A trader and his client agree a rate, a quantity and a truck. 3 min 28 s."),
    ("call2", "Call 2 · Which tile was it?", "Nobody on the call knows the tile's name; the label on the box is hidden. 1 min 19 s."),
    ("call3", "Call 3 · The call-back", "He rings back and the tile's name is said clearly. 49 s."),
]


def main() -> None:
    index = []
    for folder, title, note in CALLS:
        src = REAL / folder
        audio = next(src.glob("call.*"))
        dst = OUT / folder
        if dst.exists():
            shutil.rmtree(dst)
        (dst / "segments").mkdir(parents=True)
        shutil.copy(audio, dst / audio.name)
        for seg in sorted((src / "segments").glob("seg*.wav")):
            shutil.copy(seg, dst / "segments" / seg.name)
        index.append({"id": folder, "title": title, "note": note, "audio": audio.name})
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(index)} samples in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
