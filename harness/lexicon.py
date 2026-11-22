"""Does a lexicon shared between users make a new user's names right sooner? A simulation on real recordings.

    uv run python -m harness.lexicon --set fresh --split fresh --users 10

The recordings are dealt out to K simulated users and played in a random order. Each user confirms the
names said in their own recordings, as the page asks a real person to do. Two ways to run it:

  alone    a user's Parakh knows only the names that user confirmed earlier
  shared   it also offers, as candidates, names that at least two OTHER users have confirmed
           (harness.memory.shared_names): the audio must still back them

Reported for the mentions that matter, names the user has never confirmed: how many the base model
got right, how many Parakh got right alone, and how many with the shared lexicon. Only the people's
answers are simulated; the audio and the pipeline are real.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter

from harness import fleurs
from harness.context import ContextIndex
from harness.fleurs import CFG, RUNS_DIR, load
from harness.ice import WITNESSES
from harness.parakh import run
from harness.phonetic import is_devanagari
from harness.pronounce import pronunciations
from harness.score import score_clip


def play(rows: list[dict], users: int, seed: int, said: dict[str, str], min_users: int = 2) -> list[dict]:
    order = rows[:]
    random.Random(seed).shuffle(order)
    owner = {r["id"]: k % users for k, r in enumerate(order)}
    confirmed: dict[int, set[str]] = {u: set() for u in range(users)}
    out = []
    for k, row in enumerate(order):
        u = owner[row["id"]]
        mine = sorted(confirmed[u])
        others = Counter(n for v, names in confirmed.items() if v != u for n in names)
        shared = sorted(n for n, c in others.items() if c >= min_users and n not in confirmed[u])
        variants = [[n, said[n]] if n in said else [n] for n in row["names"]]
        results = {}
        for mode, index in (("alone", ContextIndex({"brands": mine}, said)), ("shared", ContextIndex({"brands": mine, "found": shared}, said))):
            r = run(row["audio"], index, CFG, WITNESSES)
            results[mode] = score_clip(row["ref"], r["text"].replace("\n", " "), variants, [], [])["entity_hits"]
            if mode == "alone":
                base_hits = score_clip(row["ref"], r["trace"]["witnesses"][r["trace"]["base"]].replace("\n", " "), variants, [], [])["entity_hits"]
        for i, n in enumerate(row["names"]):
            out.append({"at": k, "user": u, "name": n, "known": n in confirmed[u], "shared": n in shared,
                        "base": bool(base_hits[i]), "alone": bool(results["alone"][i]), "with_shared": bool(results["shared"][i])})
        confirmed[u] |= set(row["names"])  # the user confirms their own names after the recording
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="fresh", choices=list(fleurs.SETS))
    ap.add_argument("--split", default="fresh")
    ap.add_argument("--users", type=int, default=10)
    ap.add_argument("--orders", type=int, default=3)
    args = ap.parse_args()
    fleurs.use(args.set)
    rows = load(args.split)
    context = json.loads((fleurs.DIR / "context.json").read_text(encoding="utf-8"))["brands"]
    said = pronunciations([n for n in context if not is_devanagari(n)])
    everything = [m for seed in range(args.orders) for m in play(rows, args.users, seed, said)]

    def line(label, ms):
        n = len(ms) or 1
        return f"| {label} | {len(ms)} | {100 * sum(m['base'] for m in ms) / n:.1f}% | {100 * sum(m['alone'] for m in ms) / n:.1f}% | {100 * sum(m['with_shared'] for m in ms) / n:.1f}% |"

    new = [m for m in everything if not m["known"]]
    table = ["| Names, per mention | Mentions | Base model | Parakh, this user's names only | Parakh, plus names two other users confirmed |", "|---|---|---|---|---|",
             line("Never confirmed by this user, but by two others", [m for m in new if m["shared"]]),
             line("Never confirmed by this user, nor by two others", [m for m in new if not m["shared"]]),
             line("All names new to this user", new),
             line("Confirmed by this user before", [m for m in everything if m["known"]])]
    gained = sum(m["with_shared"] and not m["alone"] for m in new) / args.orders
    lost = sum(m["alone"] and not m["with_shared"] for m in new) / args.orders
    head = (f"Shared lexicon, FLEURS Hindi ({args.set} set): {len(rows)} recordings dealt to {args.users} simulated users, {args.orders} random orders. "
            f"Sharing fixed {gained:.1f} and lost {lost:.1f} of a user's never-confirmed names per pass.")
    print("\n" + head + "\n\n" + "\n".join(table))
    RUNS_DIR.mkdir(exist_ok=True)
    (RUNS_DIR / f"lexicon-{args.split}.md").write_text(head + "\n\n" + "\n".join(table) + "\n", encoding="utf-8")
    (RUNS_DIR / f"lexicon-{args.split}.json").write_text(json.dumps({"mentions": everything, "users": args.users, "orders": args.orders}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
