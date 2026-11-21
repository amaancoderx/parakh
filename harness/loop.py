"""Does Parakh get better as a person uses it? A simulation on real recordings.

    uv run python -m harness.loop --set fresh --split fresh

The recordings are played in a random order, as if they were one person's calls. Parakh
starts knowing no names. After each recording the simulated person does what the page asks
a real one to do: confirms the names that were said in it. A name said in a later recording
is then either new (never confirmed) or known (confirmed after an earlier recording).

Only the person's answers are simulated: they come from the reference transcript. The audio,
the recognisers and the pipeline are the real ones, and no recording is ever checked against
its own answers.

Reported: names right for new and for known names, base model against Parakh, and how the
overall figure moves from the first quarter of the recordings to the last.
"""

from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor

from harness import fleurs
from harness.context import ContextIndex
from harness.fleurs import CFG, RUNS_DIR, load
from harness.ice import WITNESSES
from harness.parakh import run
from harness.phonetic import is_devanagari
from harness.pronounce import pronunciations
from harness.score import score_clip


def play(rows: list[dict], seed: int, said: dict[str, str]) -> list[dict]:
    """One pass in one order. Returns a record per name mention: place in the order, known or new, right or not."""
    order = rows[:]
    random.Random(seed).shuffle(order)
    known_before, known = [], []
    for row in order:  # what the person had confirmed before each recording depends only on the order
        known_before.append(list(known))
        known += [n for n in row["names"] if n not in known]

    def one(k: int) -> list[dict]:
        row, names = order[k], known_before[k]
        out = run(row["audio"], ContextIndex({"brands": names}, said), CFG, WITNESSES)
        variants = [[n, said[n]] if n in said else [n] for n in row["names"]]
        ours = score_clip(row["ref"], out["text"].replace("\n", " "), variants, [], [])["entity_hits"]
        base = score_clip(row["ref"], out["trace"]["witnesses"][out["trace"]["base"]].replace("\n", " "), variants, [], [])["entity_hits"]
        return [{"at": k, "id": row["id"], "name": n, "known": n in names, "right": bool(o), "base_right": bool(b),
                 "extra_listens": out["trace"].get("extra_passes", 0)} for n, o, b in zip(row["names"], ours, base)]

    with ThreadPoolExecutor(max_workers=3) as pool:
        return [m for mentions in pool.map(one, range(len(order))) for m in mentions]


def share(mentions: list[dict], field: str) -> float | None:
    return sum(m[field] for m in mentions) / len(mentions) if mentions else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="fresh", choices=list(fleurs.SETS))
    ap.add_argument("--split", default="fresh", choices=["dev", "test", "fresh", "all"])
    ap.add_argument("--orders", type=int, default=3, help="how many random orders to play")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    fleurs.use(args.set)
    rows = load(args.split)[: args.limit or None]
    context = json.loads((fleurs.DIR / "context.json").read_text(encoding="utf-8"))["brands"]
    said = pronunciations([n for n in context if not is_devanagari(n)])
    passes = [play(rows, seed, said) for seed in range(args.orders)]

    def pct(x: float | None) -> str:
        return "n/a" if x is None else f"{100 * x:.1f}%"

    everything = [m for p in passes for m in p]
    groups = {"new": [m for m in everything if not m["known"]], "known": [m for m in everything if m["known"]]}
    quarter = max(1, len(rows) // 4)
    table = ["| Names | Mentions | Base model | Parakh |", "|---|---|---|---|"]
    table.append(f"| Heard for the first time | {len(groups['new'])} | {pct(share(groups['new'], 'base_right'))} | {pct(share(groups['new'], 'right'))} |")
    table.append(f"| Confirmed after an earlier recording | {len(groups['known'])} | {pct(share(groups['known'], 'base_right'))} | {pct(share(groups['known'], 'right'))} |")
    for label, lo, hi in (("First quarter of the recordings", 0, quarter), ("Last quarter of the recordings", len(rows) - quarter, len(rows))):
        part = [m for m in everything if lo <= m["at"] < hi]
        table.append(f"| {label} | {len(part)} | {pct(share(part, 'base_right'))} | {pct(share(part, 'right'))} |")
    per_order = [f"order {k}: known {pct(share([m for m in p if m['known']], 'base_right'))} -> {pct(share([m for m in p if m['known']], 'right'))} "
                 f"({sum(m['known'] for m in p)} mentions; fixed {sum(m['right'] and not m['base_right'] for m in p if m['known'])}, "
                 f"lost {sum(m['base_right'] and not m['right'] for m in p if m['known'])})" for k, p in enumerate(passes)]
    head = (f"Learning loop, FLEURS Hindi ({args.set} set): {len(rows)} recordings played in {args.orders} random orders, "
            f"{len(everything) // args.orders} name mentions per order. Parakh starts with no names; after each recording its names are confirmed.")
    print(f"\n{head}\n\n" + "\n".join(table) + "\n\n" + "\n".join(per_order))
    RUNS_DIR.mkdir(exist_ok=True)
    stem = f"loop-{args.split}"
    (RUNS_DIR / f"{stem}.md").write_text(head + "\n\n" + "\n".join(table) + "\n\n" + "\n".join(per_order) + "\n", encoding="utf-8")
    (RUNS_DIR / f"{stem}.json").write_text(json.dumps({"orders": passes, "recordings": len(rows)}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
