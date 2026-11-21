"""Paired bootstrap for a difference between two systems scored on the same clips.

    uv run python -m harness.stats runs/fleurs-test.json Parakh saaras-v4

Resamples clips (not individual names), since names in one clip are not independent.
Prints the difference in names right and in word error rate with a 95% interval;
an interval that excludes zero is a difference unlikely to be chance.
"""

from __future__ import annotations

import json
import math
import random
import sys
from statistics import NormalDist


def names_right(rows: list[dict]) -> float:
    hits = [h for r in rows for h in r["entity_hits"]]
    return sum(hits) / len(hits) if hits else 0.0


def wer(rows: list[dict]) -> float:
    return sum(r["errors"] for r in rows) / max(1, sum(r["ref_tokens"] for r in rows))


def paired_bootstrap(a: list[dict], b: list[dict], metric, samples: int = 4000, seed: int = 7) -> tuple[float, float, float]:
    """(difference a - b, 2.5th percentile, 97.5th percentile) over clips resampled with replacement."""
    by_id = {r["id"]: r for r in b}
    pairs = [(r, by_id[r["id"]]) for r in a if r["id"] in by_id]
    rng = random.Random(seed)
    diffs = []
    for _ in range(samples):
        pick = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        diffs.append(metric([x for x, _ in pick]) - metric([y for _, y in pick]))
    diffs.sort()
    point = metric([x for x, _ in pairs]) - metric([y for _, y in pairs])
    return point, diffs[int(0.025 * samples)], diffs[int(0.975 * samples)]


def mcnemar(a: list[dict], b: list[dict]) -> tuple[int, int, float]:
    """Exact two-sided McNemar on name mentions: (a right where b wrong, b right where a wrong, p)."""
    by_id = {r["id"]: r for r in b}
    wins = losses = 0
    for r in a:
        if r["id"] not in by_id:
            continue
        for ha, hb in zip(r["entity_hits"], by_id[r["id"]]["entity_hits"]):
            wins += ha and not hb
            losses += hb and not ha
    n, k = wins + losses, min(wins, losses)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)
    return wins, losses, p


def min_detectable(n: int, disagree: float, power: float = 0.8) -> float:
    """Smallest gain in names right (as a fraction) detectable with n mentions (Connor's formula)."""
    za, zb = NormalDist().inv_cdf(0.975), NormalDist().inv_cdf(power)
    d = 0.001
    while d < disagree:
        if ((za * math.sqrt(disagree) + zb * math.sqrt(disagree - d * d)) / d) ** 2 <= n:
            return d
        d += 0.001
    return disagree


def main() -> None:
    path, a_name, b_name = sys.argv[1:4]
    clips = json.load(open(path, encoding="utf-8"))["clips"]
    a, b = clips[a_name], clips[b_name]
    for label, metric in (("names right", names_right), ("word error rate", wer)):
        d, lo, hi = paired_bootstrap(a, b, metric)
        print(f"{a_name} minus {b_name}, {label}: {100 * d:+.1f} points (95% interval {100 * lo:+.1f} to {100 * hi:+.1f}), {len(a)} clips")
    wins, losses, p = mcnemar(a, b)
    n = sum(len(r["entity_hits"]) for r in a)
    mde = min_detectable(n, max((wins + losses) / n, 0.01)) if n else 0
    print(f"  name mentions {n}: {a_name} alone right {wins}, {b_name} alone right {losses}, exact McNemar p = {p:.4f}; "
          f"smallest gain this set can detect at 80% power: {100 * mde:.1f} points")


if __name__ == "__main__":
    main()
