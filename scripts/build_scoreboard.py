"""Collect the measured results into data/scoreboard.json for the demo page and the slides.

    uv run python scripts/build_scoreboard.py

Reads the held-out runs (runs/fleurs-test.json, runs/ice-test.json) and rescoring of the
real calls. Nothing here calls an API unless a cached response is missing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from harness.stats import mcnemar, names_right, paired_bootstrap, wer  # noqa: E402

LABELS = {
    "Parakh": "Parakh",
    "saaras-v4": "Saaras v4",
    "saaras-v3": "Saaras v3",
    "gpt-transcribe": "gpt-transcribe",
    "gpt-transcribe + its keyword list": "gpt-transcribe + its keyword list",
    "saaras-v4 + its keyword list": "Saaras v4 + its keyword list",
    "Parakh, own lookup": "Parakh, own lookup",
    "saaras-v4 + its keyword list, alphabetical": "Saaras v4 + its keyword list, A to Z",
    "Parakh on saaras-v3": "Parakh on Saaras v3",
    "Parakh on gpt-transcribe": "Parakh on gpt-transcribe",
}
RUNS = ROOT / "runs"


def on_each_base(path: Path) -> list[dict]:
    """Parakh written onto each recogniser's transcript: that recogniser alone, then with Parakh."""
    clips = json.loads(path.read_text(encoding="utf-8"))["clips"]
    out = []
    for base, ours in (("saaras-v3", "Parakh on saaras-v3"), ("saaras-v4", "Parakh"), ("gpt-transcribe", "Parakh on gpt-transcribe")):
        out.append({"base": LABELS[base], "base_names": round(100 * names_right(clips[base]), 1), "base_wer": round(100 * wer(clips[base]), 1),
                    "names_right": round(100 * names_right(clips[ours]), 1), "wer": round(100 * wer(clips[ours]), 1),
                    **{k: v for k, v in versus(clips, ours, base).items() if k != "against"}})
    return out


def funnel(which: str = "fresh") -> dict:
    """How many words reach each layer on held-out FLEURS recordings, with the full name list."""
    from harness import fleurs
    from harness.context import ContextIndex
    from harness.fleurs import CFG, load
    from harness.ice import WITNESSES
    from harness.parakh import disputed_positions, run
    from harness.phonetic import is_devanagari
    from harness.pronounce import pronunciations

    fleurs.use(which)
    context = json.loads((fleurs.DIR / "context.json").read_text(encoding="utf-8"))["brands"]
    index = ContextIndex({"brands": context}, pronunciations([n for n in context if not is_devanagari(n)]))
    out = dict(recordings=0, words=0, doubted=0, names_considered=0, recordings_heard_again=0, extra_listens=0, names_written=0, flagged_unsure=0, names_fixed=0)
    base_hits = {c["id"]: c for c in json.loads((RUNS / ("fleurs-fresh-bases.json" if which == "fresh" else "fleurs-test-bases.json")).read_text(encoding="utf-8"))["clips"]["saaras-v4"]}
    ours = {c["id"]: c for c in json.loads((RUNS / ("fleurs-fresh-bases.json" if which == "fresh" else "fleurs-test-bases.json")).read_text(encoding="utf-8"))["clips"]["Parakh"]}
    for row in load("fresh" if which == "fresh" else "test"):
        t = run(row["audio"], index, CFG, WITNESSES)["trace"]
        out["names_fixed"] += sum(a and not b for a, b in zip(ours[row["id"]]["entity_hits"], base_hits[row["id"]]["entity_hits"]))
        out["recordings"] += 1
        out["words"] += len(t["witnesses"][t["base"]].split())
        out["doubted"] += len(disputed_positions(t["witnesses"])[t["base"]])
        out["names_considered"] += len(t.get("shortlist", []))
        out["recordings_heard_again"] += bool(t.get("extra_passes"))
        out["extra_listens"] += t.get("extra_passes", 0)
        out["names_written"] += len(t.get("edits", []))
        out["flagged_unsure"] += len(t.get("unsure_spans", []))
    fleurs.use("first")
    return out


def whole(clips: dict, ours: str = "Parakh", base: str = "saaras-v4") -> dict:
    """Recordings in which every name is right: what an action taken on the recording depends on."""
    def rate(name: str) -> float:
        return round(100 * sum(all(s["entity_hits"]) for s in clips[name]) / len(clips[name]), 1)

    by_id = {s["id"]: s for s in clips[base]}
    fixed = sum(all(s["entity_hits"]) and not all(by_id[s["id"]]["entity_hits"]) for s in clips[ours])
    broken = sum(all(by_id[s["id"]]["entity_hits"]) and not all(s["entity_hits"]) for s in clips[ours])
    return {"base": rate(base), "parakh": rate(ours), "recordings": len(clips[ours]), "fixed": fixed, "broken": broken}


def clear_and_right() -> dict:
    """On the fresh set: recordings Parakh raised no question on, and how many of those had every name right."""
    from harness import fleurs
    from harness.context import ContextIndex
    from harness.ice import WITNESSES
    from harness.parakh import run
    from harness.phonetic import is_devanagari
    from harness.pronounce import pronunciations
    from harness.score import score_clip

    fleurs.use("fresh")
    context = json.loads((fleurs.DIR / "context.json").read_text(encoding="utf-8"))["brands"]
    said = pronunciations([n for n in context if not is_devanagari(n)])
    index = ContextIndex({"brands": context}, said)
    out = dict(recordings=0, right=0, asked=0, asked_right=0)
    for row in fleurs.load("fresh"):
        r = run(row["audio"], index, fleurs.CFG, WITNESSES)
        t = r["trace"]
        hits = score_clip(row["ref"], r["text"].replace("\n", " "), [[n, said[n]] if n in said else [n] for n in row["names"]], [], [])["entity_hits"]
        if t.get("unsure_spans") or t.get("number_doubts") or t.get("unresolved"):
            out["asked"] += 1
            out["asked_right"] += all(hits)
        else:
            out["recordings"] += 1
            out["right"] += all(hits)
    fleurs.use("first")
    return out


def loop(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    mentions = [m for order in data["orders"] for m in order]
    known, new = [m for m in mentions if m["known"]], [m for m in mentions if not m["known"]]

    def pct(ms: list[dict], field: str) -> float:
        return round(100 * sum(m[field] for m in ms) / max(1, len(ms)), 1)

    first = data["orders"][0]
    return {"orders": len(data["orders"]), "recordings": data["recordings"],
            "known": pct(known, "right"), "known_base": pct(known, "base_right"), "known_mentions": len(known) // len(data["orders"]),
            "new": pct(new, "right"), "new_base": pct(new, "base_right"), "new_mentions": len(new) // len(data["orders"]),
            "fixed": sum(m["right"] and not m["base_right"] for m in first if m["known"]),
            "lost": sum(m["base_right"] and not m["right"] for m in first if m["known"])}


def stress(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    clips = data["clips"]
    rows = [{"system": LABELS[n], "sound_alikes_written": sum(len(s["decoys_written"]) for s in ss),
             "names_right": round(100 * names_right(ss), 1), "wer": round(100 * wer(ss), 1)} for n, ss in clips.items()]
    rows.sort(key=lambda r: (r["sound_alikes_written"], -r["names_right"]))

    def lost(ours: str, ref: str) -> int:  # right names the list made it lose
        by_id = {s["id"]: s for s in clips[ref]}
        return sum(1 for s in clips[ours] for a, b in zip(s["entity_hits"], by_id[s["id"]]["entity_hits"]) if b and not a)

    losses = {"Parakh": lost("Parakh", "saaras-v4"),
              "Saaras v4 + its keyword list": lost("saaras-v4 + its keyword list", "saaras-v4"),
              "gpt-transcribe + its keyword list": lost("gpt-transcribe + its keyword list", "gpt-transcribe")}
    if "saaras-v4 + its keyword list, alphabetical" in clips:
        losses["Saaras v4 + its keyword list, A to Z"] = lost("saaras-v4 + its keyword list, alphabetical", "saaras-v4")
    return {"clips": len(clips["Parakh"]), "planted": data["traps"], "rows": rows, "right_names_lost": losses}



def versus(clips: dict, a: str, b: str) -> dict:
    d, lo, hi = paired_bootstrap(clips[a], clips[b], names_right)
    wd, wlo, whi = paired_bootstrap(clips[a], clips[b], wer)
    wins, losses, p = mcnemar(clips[a], clips[b])
    return {"against": LABELS[b], "names_points": round(100 * d, 1), "names_ci": [round(100 * lo, 1), round(100 * hi, 1)],
            "wer_points": round(100 * wd, 1), "wer_ci": [round(100 * wlo, 1), round(100 * whi, 1)],
            "only_parakh_right": wins, "only_other_right": losses, "p": round(p, 4)}


def benchmark(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    clips = data["clips"]
    rows = [{
        "system": LABELS[name],
        "names_right": round(100 * names_right(ss), 1),
        "wer": round(100 * wer(ss), 1),
        "written_not_said": sum(len(s["false_insertions"]) for s in ss),
    } for name, ss in clips.items() if not name.startswith("Parakh on ")]
    rows.sort(key=lambda r: -r["names_right"])
    any_ss = next(iter(clips.values()))
    return {
        "clips": len(any_ss),
        "mentions": sum(len(s["entity_hits"]) for s in any_ss),
        "rows": rows,
        "versus": [versus(clips, "Parakh", b) for b in ("saaras-v4", "gpt-transcribe + its keyword list", "saaras-v4 + its keyword list")],
        "extra_listens": sum(1 for s in clips["Parakh"] if s.get("extra_passes")),
    }


def main() -> None:
    out = {}
    out["fleurs"] = {
        "title": "FLEURS Hindi (Google), held-out",
        "note": "Real read speech. One rule changed after the first full run: when two recognisers agree on a word, their spelling is now offered to the second listen in the transcript's own script. That cut the planted sound-alikes Parakh wrote from 10 to 6 and cost two right names here (97.9% before, 96.4% now).",
        **benchmark(ROOT / "runs" / "fleurs-test.json"),
    }
    out["ice"] = {
        "title": "IndicContextEval Hindi (AI4Bharat), held-out",
        "note": "Lecture speech with English technical terms, 26 speakers. The benchmark's own term lists rarely contain what the recognisers miss.",
        **benchmark(ROOT / "runs" / "ice-test.json"),
    }
    if (RUNS / "fleurs-test-bases.json").exists():
        out["bases"] = {"rows": on_each_base(RUNS / "fleurs-test-bases.json"),
                        "note": "The same checks written onto each recogniser's own transcript, as if that were the one you already run."}
    if (RUNS / "stress-test.json").exists():
        out["stress"] = {**stress(RUNS / "stress-test.json"),
                         "note": "The same recordings. Each one's own names were taken off the list and a sound-alike put in for each (ईरान -> इराक). Writing one means writing the wrong person or place."}
    if (RUNS / "fleurs-test-bases-phone.json").exists():
        phone = benchmark(RUNS / "fleurs-test-bases-phone.json")
        out["phone"] = {**phone, "bases": on_each_base(RUNS / "fleurs-test-bases-phone.json"),
                        "note": "The same recordings passed through a phone line first: 300-3400 Hz, 8 kHz, G.711 mu-law."}
    try:
        out["funnel"] = funnel("fresh" if (RUNS / "fleurs-fresh-bases.json").exists() else "first")
    except Exception as e:  # the public recordings are not in the repository
        print("funnel skipped:", e)
    if (RUNS / "numbers.json").exists():
        n = json.loads((RUNS / "numbers.json").read_text(encoding="utf-8"))
        out["numbers"] = {**n, "note": "Every number in a reference, counted right when its value is in the transcript. Parakh writes digits by rule, fixes a number only when both other recognisers heard another value or the speakers' own multiplication settles it, and asks otherwise."}
    if (RUNS / "latency.json").exists():
        out["latency"] = json.loads((RUNS / "latency.json").read_text(encoding="utf-8"))["summary"]
    if (RUNS / "fleurs-fresh-bases.json").exists():
        clips = json.loads((RUNS / "fleurs-fresh-bases.json").read_text(encoding="utf-8"))["clips"]
        fresh = benchmark(RUNS / "fleurs-fresh-bases.json")
        out["fresh"] = {**fresh, "bases": on_each_base(RUNS / "fleurs-fresh-bases.json"), "whole": whole(clips),
                        "whole_v3": whole(clips, "Parakh on saaras-v3", "saaras-v3"),
                        "note": "The FLEURS Hindi test split: no sentence in common with the other set, and first run after the rules were frozen. The list is every name in it."}
        az = RUNS / "fleurs-fresh-alpha.json"  # Sarvam's 50 terms in alphabetical order, as one more row
        if az.exists():
            extra = json.loads(az.read_text(encoding="utf-8"))["clips"]
            name = "saaras-v4 + its keyword list, alphabetical"
            out["fresh"]["rows"].append({"system": LABELS[name], "names_right": round(100 * names_right(extra[name]), 1),
                                         "wer": round(100 * wer(extra[name]), 1), "written_not_said": sum(len(c["false_insertions"]) for c in extra[name])})
            out["fresh"]["rows"].sort(key=lambda r: -r["names_right"])
            out["fresh"]["versus"].append(versus({**clips, name: extra[name]}, "Parakh", name))
        for file in ("stress-fresh-alpha.json", "stress-fresh.json"):
            if (RUNS / file).exists():
                out["fresh"]["stress"] = stress(RUNS / file)
                break
        if (RUNS / "loop-fresh.json").exists():
            out["fresh"]["loop"] = loop(RUNS / "loop-fresh.json")
        try:
            out["fresh"]["clear"] = clear_and_right()
        except Exception as e:
            print("clear skipped:", e)
    nc = ROOT / "runs" / "fleurs-test-nocontext-discover.json"
    if nc.exists():
        clips = json.loads(nc.read_text(encoding="utf-8"))["clips"]
        clips = {n: ss for n, ss in clips.items() if n != "Parakh"}  # with nothing to check, plain Parakh is its base
        rows = sorted(({"system": LABELS[n], "names_right": round(100 * names_right(ss), 1), "wer": round(100 * wer(ss), 1)}
                       for n, ss in clips.items()), key=lambda r: (-r["names_right"], r["wer"]))
        hits = [[h for s in clips[n] for h in s["entity_hits"]] for n in ("saaras-v4", "saaras-v3", "gpt-transcribe")]
        out["fleurs_nocontext"] = {
            "rows": rows,
            "best_possible": round(100 * sum(any(t) for t in zip(*hits)) / len(hits[0]), 1),
            "versus": versus(clips, "Parakh, own lookup", "saaras-v4"),
            "written": sum(len(s["edits"]) for s in clips["Parakh, own lookup"]),
            "note": "The same recordings with no name list given to any system. Parakh looks names up itself and writes one only if two of three extra listens write it.",
        }
    try:
        from real_calls_table import table, table_no_context
        said, nctotals = table_no_context()
        out["calls_nocontext"] = {"mentions": said, "rows": sorted(({"system": n, "right": v} for n, v in nctotals.items()), key=lambda r: -r["right"])}
        mentions, calls, totals = table()
        out["calls"] = {
            "title": "Three real trade calls",
            "note": "Names and numbers confirmed by the caller's family. Rules were developed on these calls, so this is not a held-out test.",
            "mentions": mentions, "calls": calls,
            "rows": sorted(({"system": n, "right": t["right"], "wrong_names": t["wrong"]} for n, t in totals.items()), key=lambda r: -r["right"]),
        }
    except Exception as e:  # the private calls are not in the repository
        print("real calls skipped:", e)
    (ROOT / "data" / "scoreboard.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    f = out["fleurs"]
    print("FLEURS:", [(r["system"], r["names_right"]) for r in f["rows"]], f["versus"][0])
    print("calls:", out.get("calls", {}).get("rows"))


if __name__ == "__main__":
    main()
