"""Does memory make Parakh better? The same recordings without memory and with it.

    uv run python scripts/memory_eval.py fleurs     # 189 unseen recordings, names fed once from a sheet
    uv run python scripts/memory_eval.py calls      # the three real trade calls, as a trader's week
    uv run python scripts/memory_eval.py all

fleurs: the FLEURS fresh set. Without memory, Parakh gets no names. With memory, the set's
name list is written to a spreadsheet, read by the same parser the app uses for uploads,
stored in a user's memory, and every recording is checked with that memory: nothing is sent
with the request. Recogniser answers are the cached ones the scoreboard uses.

calls: the bundled trade calls, run through the app's own call pipeline (listen, find, check,
summarise) with a fresh user, day by day:
    day 1   calls 1 and 2 arrive; memory is empty
    day 1   the trader uploads his party ledger (an .xlsx, with decoys: other parties, other brands)
    night 1 the daily learning run checks the day's calls again with the ledger
    day 2   call 3 arrives, the tile's name is said clearly; the trader taps yes on it once
    night 2 the learning run checks the week's calls again
Names are scored against data/real/truth.json.

Writes runs/memory.json and runs/memory.md.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness import account, memory, sources  # noqa: E402
from harness.data import ROOT as DATA_ROOT  # noqa: E402

RUNS = ROOT / "runs"
OUT = RUNS / "memory.json"

# A tile and steel trader's party ledger. His real parties and transport are in it, with
# others he deals with, and the tile brands he stocks, including one a caller guessed wrong.
LEDGER = [
    ("Party Name", "Mobile", "Balance", "Transport", "Item"),
    ("Mohammad bhai", "9876500001", "42000", "Eicher", "Steel drum"),
    ("Jawar sahab", "9876500002", "18500", "Tata 407", "Vitrified tile"),
    ("Gupta Traders", "9876500003", "7200", "Ashok Leyland", "Kajaria"),
    ("Sharma Tiles", "9876500004", "0", "Mahindra Pickup", "Somany"),
    ("Ramesh Steel", "9876500005", "56000", "Eicher", "MS sheet"),
    ("Singh Hardware", "9876500006", "3100", "Tata Ace", "Johnson"),
    ("Agarwal Paints", "9876500007", "900", "Bolero", "Asian Paints"),
    ("Pradeep Bhai", "9876500008", "15000", "Tata 407", "Nitco"),
    ("Imran Traders", "9876500009", "2500", "Ashok Leyland", "Orientbell"),
    ("Verma Sanitary", "9876500010", "11000", "Mahindra Pickup", "Cera"),
    ("Kishore Ji", "9876500011", "6400", "Tata Ace", "Hindware"),
    ("Babu Bhai", "9876500012", "0", "Bolero", "Jindal"),
    ("Salim Ansari", "9876500013", "8800", "Eicher", "Tata Tiscon"),
    ("Deepak Marble", "9876500014", "21000", "Tata 407", "RAK Ceramics"),
    ("Naresh Kumar", "9876500015", "1500", "Ashok Leyland", "Simpolo"),
]


def _ledger_xlsx() -> bytes:
    from openpyxl import Workbook
    book = Workbook()
    for row in LEDGER:
        book.active.append(row)
    buf = io.BytesIO()
    book.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- the trade calls

def _hits(text: str, entity: dict) -> int:
    forms = [entity["name"], *entity.get("variants", [])]
    found = sum(len(re.findall(r"(?<!\w)" + re.escape(f) + r"(?!\w)", text, flags=re.I)) for f in forms)
    return min(found, entity["count"])


def _score_call(job: dict, truth: dict) -> dict:
    text = " ".join(s.get("text", "") for s in job["segments"])
    base = " ".join(next((w["text"] for w in s.get("witnesses", []) if w["name"] == s.get("base_name")), "") for s in job["segments"])
    ents = truth["entities"]
    said = sum(e["count"] for e in ents)
    wrong = [n for n in truth.get("unconfirmed", []) if re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", text, re.I)]
    return {"names_said": said, "right": sum(_hits(text, e) for e in ents), "right_base": sum(_hits(base, e) for e in ents),
            "per_name": {e["name"]: f"{_hits(text, e)}/{e['count']}" for e in ents},
            "wrong_guess_written": wrong, "open_questions": sum(1 for q in job.get("questions", []) if not q.get("answer"))}


def calls() -> dict:
    from harness import service
    truth = json.loads((DATA_ROOT / "data" / "real" / "truth.json").read_text(encoding="utf-8"))
    user = "eval-trader"
    memory.forget(user)
    account.forget_calls(user)
    samples = {s["id"]: s for s in service._samples()}

    def run_call(sample_id: str) -> dict:
        meta = samples.get(sample_id) or {"title": sample_id, "audio": "call.mp4"}  # a call can be kept off the app's list
        folder = service.SAMPLES_DIR / sample_id
        segs = sorted((folder / "segments").glob("seg*.wav"))
        job = service._new_job(meta["title"], folder / meta["audio"], segs, user, [], discover_names=True)
        service.JOBS[job["id"]] = job
        service._work(job)
        assert job["status"] == "done", job.get("error")
        return job

    def snapshot(ids: dict[str, str]) -> dict:
        out = {}
        for sample_id, job_id in ids.items():
            job = account.load_call(job_id)["job"]
            out[sample_id] = _score_call(job, truth[sample_id])
        return out

    days = []
    ids = {}
    t0 = time.time()
    for sid in ("dad_call", "call2"):
        ids[sid] = run_call(sid)["id"]
    days.append({"when": "Day 1, memory empty", "calls": snapshot(ids), "memory": memory.load(user)["settings"] | {"names": 0}})

    # The ledger, through the same path as an upload in the app.
    names = sources.names_from_file("party-ledger.xlsx", _ledger_xlsx())
    memory.add_source(user, "ledger", {"kind": "contacts", "file": "party-ledger.xlsx", "added": time.time(), "status": "done", "count": len(names)})
    memory.confirm_many(user, names, how="from party-ledger.xlsx", source="ledger")
    night1 = service.learn(user)
    days.append({"when": "Night 1, after the ledger upload", "calls": snapshot(ids), "learning": night1,
                 "memory": {"names": len(memory.verified(user))}})

    job3 = run_call("call3")
    ids["call3"] = job3["id"]
    learned = list(memory.load(user)["candidates"])
    tapped = [n for n in learned if "arizona" in n.lower()]
    for n in tapped:  # the one tap the trader gives
        memory.confirm(user, n)
    days.append({"when": "Day 2, call 3 arrives", "calls": snapshot(ids), "heard_and_backed": learned, "tapped_yes": tapped,
                 "memory": {"names": len(memory.verified(user))}})
    night2 = service.learn(user)
    days.append({"when": "Night 2, learning run", "calls": snapshot(ids), "learning": night2,
                 "memory": {"names": len(memory.verified(user))}})
    out = {"days": days, "ledger_names": names, "took_s": round(time.time() - t0, 1)}
    memory.forget(user)
    account.forget_calls(user)
    return out


# ---------------------------------------------------------------- FLEURS fresh

def fleurs(limit: int = 0) -> dict:
    from dataclasses import replace

    from harness import fleurs as F
    from harness.context import ContextIndex
    from harness.ice import WITNESSES
    from harness.parakh import run
    from harness.phonetic import is_devanagari
    from harness.pronounce import pronunciations
    from harness.score import aggregate, score_clip

    F.use("fresh")
    rows = F.load("all")[: limit or None]
    context = json.loads((F.DIR / "context.json").read_text(encoding="utf-8"))["brands"]
    said = pronunciations([n for n in context if not is_devanagari(n)])

    # Memory, fed the way a developer would: one CSV upload, then no names on any request.
    user = "eval-dev"
    memory.forget(user)
    csv_bytes = ("Name\n" + "\n".join(context)).encode("utf-8")
    parsed = sources.names_from_file("names.csv", csv_bytes)
    memory.confirm_many(user, parsed, how="from names.csv", source="csv")
    remembered = memory.verified(user)
    with_memory = ContextIndex.build({"contacts": remembered})
    without = ContextIndex({}, None)
    cfg = replace(F.CFG)

    scored = {"without memory": [], "with memory": []}
    t0 = time.time()
    for n, row in enumerate(rows):
        ents = [[x, said[x]] if x in said else [x] for x in row["names"]]
        for label, index in (("without memory", without), ("with memory", with_memory)):
            r = run(row["audio"], index, cfg, WITNESSES)
            s = score_clip(row["ref"], r["text"], ents, [], context)
            s.update(id=row["id"], edits=r["trace"].get("edits", []), extra=r["trace"].get("extra_passes", 0))
            scored[label].append(s)
        if n % 20 == 0:
            print(f"  {n + 1}/{len(rows)}", flush=True)
    memory.forget(user)

    def summary(rs: list[dict]) -> dict:
        hits = [h for r in rs for h in r["entity_hits"]]
        errs = {}
        for r in rs:
            for k, v in r["errors_by_cat"].items():
                errs[k] = errs.get(k, 0) + v
        return {"names": len(hits), "names_right": sum(hits), "rate": round(sum(hits) / max(1, len(hits)), 4),
                "whole_recordings_right": sum(all(r["entity_hits"]) for r in rs), "recordings": len(rs),
                "errors": errs, "wer": round(sum(r["wer"] for r in rs) / max(1, len(rs)), 4), "agg": aggregate(rs)}

    a, b = scored["without memory"], scored["with memory"]
    pairs = [(x, y) for ra, rb in zip(a, b) for x, y in zip(ra["entity_hits"], rb["entity_hits"])]
    return {"recordings": len(rows), "memory_names": len(remembered), "parsed_from_csv": len(parsed), "context_names": len(context),
            "without": summary(a), "with": summary(b),
            "fixed_by_memory": sum(1 for x, y in pairs if y and not x), "broken_by_memory": sum(1 for x, y in pairs if x and not y),
            "took_s": round(time.time() - t0, 1)}


def report(res: dict) -> str:
    lines = ["# Memory: without it and with it", ""]
    if "fleurs" in res:
        f = res["fleurs"]
        w, m = f["without"], f["with"]
        lines += [f"## {f['recordings']} unseen recordings (FLEURS fresh), names fed once from a CSV into memory", "",
                  "| | Without memory | With memory |", "|---|---|---|",
                  f"| Names right | {w['names_right']}/{w['names']} ({w['rate']:.1%}) | **{m['names_right']}/{m['names']} ({m['rate']:.1%})** |",
                  f"| Recordings with every name right | {w['whole_recordings_right']}/{w['recordings']} | **{m['whole_recordings_right']}/{m['recordings']}** |",
                  f"| Word error rate | {w['wer']:.2%} | **{m['wer']:.2%}** |",
                  f"| Names fixed by memory / broken by it | | **{f['fixed_by_memory']} / {f['broken_by_memory']}** |", ""]
    if "calls" in res:
        lines += ["## Three real trade calls, as a trader's week", "", "| | Call 1 | Call 2 | Call 3 | Questions left |", "|---|---|---|---|---|"]
        for d in res["calls"]["days"]:
            c = d["calls"]
            cell = lambda k: (f"{c[k]['right']}/{c[k]['names_said']}" if k in c else "–")
            lines.append(f"| {d['when']} | {cell('dad_call')} | {cell('call2')} | {cell('call3')} | {sum(x['open_questions'] for x in c.values())} |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    res = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    if what in ("fleurs", "all"):
        res["fleurs"] = fleurs(limit)
    if what in ("calls", "all"):
        res["calls"] = calls()
    if not limit:
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        (RUNS / "memory.md").write_text(report(res), encoding="utf-8")
    print(report(res))


if __name__ == "__main__":
    main()
