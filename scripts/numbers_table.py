"""Numbers right: for every number in a reference, is its value in the transcript? Base model against Parakh.

    uv run python scripts/numbers_table.py            # both public sets, saved responses only

Parakh's number rules: digits by rule, a fix when both other recognisers agree on another value,
a fix or a dropped doubt when the speakers' own multiplication settles it, a question otherwise.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import fleurs  # noqa: E402
from harness.context import ContextIndex  # noqa: E402
from harness.ice import WITNESSES  # noqa: E402
from harness.numbers import numbers_in  # noqa: E402
from harness.parakh import run  # noqa: E402
from harness.phonetic import clean_devanagari, is_devanagari  # noqa: E402
from harness.pronounce import pronunciations  # noqa: E402

RUNS = Path(__file__).resolve().parent.parent / "runs"


def values(text: str) -> Counter:
    return Counter(n["value"] for n in numbers_in(clean_devanagari(text)))


def table(which: str, split: str) -> dict:
    fleurs.use(which)
    context = json.loads((fleurs.DIR / "context.json").read_text(encoding="utf-8"))["brands"]
    index = ContextIndex({"brands": context}, pronunciations([n for n in context if not is_devanagari(n)]))
    out = {"recordings": 0, "numbers": 0, "base_right": 0, "parakh_right": 0, "fixed": 0, "broken": 0, "asked": 0, "edits": []}
    for row in fleurs.load(split):
        r = run(row["audio"], index, fleurs.CFG, WITNESSES)
        t = r["trace"]
        ref = values(row["ref"])
        if not ref:
            continue
        base, ours = values(t["witnesses"][t["base"]]), values(r["text"])
        out["recordings"] += 1
        for v, k in ref.items():
            out["numbers"] += k
            b, o = min(k, base[v]), min(k, ours[v])
            out["base_right"] += b
            out["parakh_right"] += o
            out["fixed"] += max(0, o - b)
            out["broken"] += max(0, b - o)
        out["asked"] += len(t.get("number_doubts", []))
        out["edits"] += [(e["from"], e["to"], e["why"]) for e in t.get("edits", []) if e.get("kind") == "number"]
    fleurs.use("first")
    return out


def main() -> None:
    result = {"first": table("first", "test"), "fresh": table("fresh", "fresh")}
    for which, o in result.items():
        print(f"{which}: {o['numbers']} numbers in {o['recordings']} recordings | base right {o['base_right']} | Parakh right {o['parakh_right']} "
              f"(fixed {o['fixed']}, broken {o['broken']}) | asked {o['asked']} | edits {o['edits']}")
    RUNS.mkdir(exist_ok=True)
    (RUNS / "numbers.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
