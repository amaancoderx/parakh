"""Run a real call recording through Parakh, end to end.

    uv run python -m harness.call <recording> --name call2 --user dad
    uv run python -m harness.call <recording> --name call2 --context contacts.json --no-discover

1. Split the recording at pauses and transcribe every segment with each recogniser.
2. Discover: with no context given, work out the topic and which real-world names
   the garbled words could be (harness/discover.py).
3. Hear: write a name into the transcript only if the audio backs it (harness/parakh.py).
4. Remember: names that passed are saved for this user and trusted in later calls.

Everything is written under data/real/<name>/, which git ignores.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from harness import memory
from harness.context import ContextIndex
from harness.data import ROOT
from harness.discover import discover
from harness.numbers import find_numbers, to_digits
from harness.parakh import Config, run
from harness.phonetic import same_sound
from harness.segment import split
from harness.systems import available_systems

REAL_DIR = ROOT / "data" / "real"


def process_call(
    recording: Path | None,
    name: str,
    user: str | None = None,
    context_path: Path | None = None,
    use_discovery: bool = True,
    cfg: Config | None = None,
) -> dict:
    cfg = cfg or Config()
    out_dir = REAL_DIR / name
    seg_dir = out_dir / "segments"
    segments = sorted(seg_dir.glob("seg*.wav"))
    if not segments:
        if recording is None:
            raise SystemExit(f"no segments under {seg_dir} and no recording given")
        out_dir.mkdir(parents=True, exist_ok=True)
        source = out_dir / f"call{recording.suffix.lower()}"
        shutil.copy(recording, source)
        segments = split(source, seg_dir)

    systems = available_systems()
    heard = [{w: systems[w](seg)["text"].replace("\n", " ") for w in cfg.witnesses} for seg in segments]

    typed = json.loads(context_path.read_text(encoding="utf-8")) if context_path else {}
    trusted = memory.verified(user) if user else []  # confirmed by the user: trusted like contacts
    pending = memory.candidates(user) if user else []  # heard before, not confirmed: still need backing
    found = discover(heard) if use_discovery else {"topic": "", "candidates": [], "people": []}
    index = ContextIndex.build({
        "contacts": typed.get("contacts", []),
        "places": typed.get("places", []),
        "brands": [*typed.get("brands", []), *trusted],
        "found": [*pending, *found["candidates"]],
    })

    results, learned = [], {}
    for seg, h in zip(segments, heard):
        r = run(seg, index, cfg, systems)
        t = r["trace"]
        for nm in t.get("found", []):
            learned[nm] = {"from": name, "evidence": "proposed by the topic search and written unprompted by a recogniser"}
        results.append({
            "seg": seg.stem,
            "heard": h,
            "base": h[cfg.base],
            "text": r["text"].replace("\n", " "),
            "dictated": to_digits(r["text"].replace("\n", " ")),  # the same text with spoken numbers as digits
            "numbers": [{"said": n["text"], "value": n["value"]} for n in find_numbers(r["text"].replace("\n", " "))],
            "edits": t.get("edits", []),
            "suggested": t.get("suggested", []),
            "unresolved": t.get("unresolved", []),
            "votes": t.get("votes", {}),
            "corroborated": t.get("corroborated", []),
            "latency_s": r["latency_s"],
        })
    to_confirm = memory.propose(user, learned) if user and learned else []
    if user:
        memory.touch(user, [e["to"] for r in results for e in r["edits"]])

    # People's names the recognisers disagree on stay open unless saved context settled them.
    settled = [e["to"] for r in results for e in r["edits"]]
    people = [
        [v.strip() for h in ([p["heard"]] if isinstance(p["heard"], str) else p["heard"]) for v in str(h).split(" / ")]
        for p in found.get("people", [])
    ]
    unsure_people = [
        heard_as for heard_as in people
        if not any(same_sound(h, s, strict_final=True) for h in heard_as for s in settled)
    ]
    out = {
        "call": name,
        "topic": found["topic"],
        "segments": results,
        "learned": sorted(learned),
        "to_confirm": to_confirm,
        "memory_used": {"verified": trusted, "candidates": pending},
        "unsure_people": unsure_people,
    }
    (out_dir / "parakh.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def report(out: dict) -> None:
    print(f"\n#### {out['call']}\ntopic: {out['topic'] or '(discovery off)'}")
    if out["memory_used"]["verified"] or out["memory_used"]["candidates"]:
        print("started with memory:", out["memory_used"])
    for r in out["segments"]:
        for e in r["edits"]:
            why = "a recogniser wrote it unprompted" if e["to"] in r["corroborated"] else f"won the hearing vote {r['votes']}" if r["votes"] else "the hinted pass chose it"
            print(f"  {r['seg']}  FIXED   {e['from']!r} -> {e['to']!r}   ({why})")
        for s in r["suggested"]:
            print(f"  {r['seg']}  SUGGEST did you mean {s!r}? (not written: no recogniser heard it unprompted)")
        for u in r["unresolved"]:
            print(f"  {r['seg']}  UNSURE  could not choose between {u}")
    for heard in out["unsure_people"]:
        print(f"  UNSURE person's name, recognisers disagree: {heard}")
    print("heard and backed by the audio:", out["learned"] or "nothing new")
    if out["to_confirm"]:
        print("ask the user to confirm:", out["to_confirm"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("recording", type=Path, nargs="?")
    ap.add_argument("--name", required=True, help="folder name under data/real/")
    ap.add_argument("--user", help="whose memory to read and add to; omit for no memory")
    ap.add_argument("--context", type=Path, help="typed context JSON (contacts, places, brands)")
    ap.add_argument("--no-discover", action="store_true", help="skip the topic search")
    args = ap.parse_args()
    report(process_call(args.recording, args.name, args.user, args.context, not args.no_discover))


if __name__ == "__main__":
    main()
