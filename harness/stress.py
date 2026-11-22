"""Stress test: the right name is NOT on the list, and a sound-alike is.

    uv run python -m harness.stress --decoys          # write the sound-alikes once, and print them
    uv run python -m harness.stress --split dev
    uv run python -m harness.stress --split test       # final numbers only

Same FLEURS Hindi recordings as harness.fleurs. A real contact list never holds every name
a caller says, and it is full of names that sound like the ones it lacks. So for each
recording we take the usual list of 100 names, remove the names actually said in it, and
add one sound-alike per removed name: a different real name that sounds similar (ईरान ->
इराक), written once by an OpenAI text model and saved in decoys.json. Every context-aware
system gets that list for that recording.

A system that trusts its list writes the sound-alike: the wrong person, the wrong place.
Scored: sound-alikes written, any list name written that was not said, true names still
right, and word error rate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from harness.asr import client, transcribe
from harness.context import ContextIndex
from harness import fleurs
from harness.fleurs import CFG, RUNS_DIR, load
from harness.ice import SCRIPT, WITNESSES
from harness.parakh import run, sarvam_with_list
from harness.phonetic import is_devanagari, same_sound, similarity
from harness.pronounce import pronunciations
from harness.score import aggregate, false_insertions, score_clip, span_hit
from harness.stats import paired_bootstrap
from harness.systems import _cached, _sarvam

PROMPT = (
    "For each name in the JSON list, give ONE different real name that a listener could mistake it for when "
    "it is spoken aloud: a different real person, place, organisation or thing whose name sounds similar "
    "(ईरान -> इराक, ऑस्ट्रेलिया -> ऑस्ट्रिया, अर्जेंटीना -> अल्जीरिया, स्वीडन -> स्वाज़ीलैंड). It must be a genuinely "
    "different name, never another spelling or a longer form of the same one, and it must differ in at least "
    "one clearly audible consonant or syllable. Keep the same number of words where you can. Write it in "
    "Devanagari the way Hindi news writes it. Reply with only a JSON object mapping every input name, "
    "unchanged, to its sound-alike."
)


def decoys(names: list[str]) -> dict[str, str]:
    """name -> a different, similar-sounding real name. Asked once, then read from decoys.json."""
    file = fleurs.DIR / "decoys.json"
    saved = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    missing = [n for n in names if n not in saved]
    if missing:
        resp = client().chat.completions.create(
            model="gpt-5.5", reasoning_effort="low", response_format={"type": "json_object"},
            messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": json.dumps(missing, ensure_ascii=False)}],
        )
        got = json.loads(resp.choices[0].message.content or "{}")
        saved.update({n: got[n].strip() for n in missing if isinstance(got.get(n), str) and got[n].strip()})
        file.write_text(json.dumps(saved, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    # A usable sound-alike is close in sound but not the same sound (that would be a respelling).
    return {n: d for n, d in saved.items() if n in names and not same_sound(n, d) and similarity(n, d) >= 0.4}


def clip_list(row: dict, context: list[str], decoy: dict[str, str]) -> tuple[list[str], list[str]]:
    """(the list this recording's systems get, the sound-alikes in it). No name said in the recording is on it."""
    def said_here(name: str) -> bool:
        return span_hit([name], row["ref"], strict=True) or any(same_sound(name, n) for n in row["names"])

    traps = [d for d in dict.fromkeys(decoy[n] for n in row["names"] if n in decoy) if not said_here(d)]
    others = [n for n in context if not said_here(n) and n not in traps]
    return traps + others, traps


def sarvam_terms(row: dict, terms: list[str], traps: list[str]) -> list[str]:
    """Sarvam takes 50 terms: the sound-alikes first (where harness.fleurs puts the true names), then others."""
    others = sorted((n for n in terms if n not in traps), key=lambda n: hashlib.sha1((row["id"] + n).encode()).hexdigest())
    return (traps + others)[:50]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="first", choices=list(fleurs.SETS))
    ap.add_argument("--split", default="dev", choices=["dev", "test", "fresh", "all"])
    ap.add_argument("--limit", type=int, default=0, help="first N utterances only")
    ap.add_argument("--decoys", action="store_true", help="write and print the sound-alikes, then stop")
    ap.add_argument("--stack", action="store_true", help="also run Parakh on Sarvam-with-its-keyword-feature, the 50 names chosen by Parakh")
    ap.add_argument("--both", action="store_true", help="keep the true names in the list too: two contacts that sound alike, who was it?")
    ap.add_argument("--acoustic", action="store_true", help="let the acoustic arbiter settle sound-alike groups the hinted listens cannot")
    ap.add_argument("--vote", default="", choices=["", "2of3", "openai+1"], help="use the vendors' keyword features as votes")
    ap.add_argument("--jury", type=int, default=0, help="how many of the three second listens must write a name (0: the usual single listen)")
    ap.add_argument("--real", action="store_true", help="also run the keyword features as a product could: 50 of the list for Sarvam, all of it for OpenAI")
    ap.add_argument("--alpha", action="store_true", help="also give Sarvam its 50 terms in alphabetical order, not with the sound-alikes first")
    args = ap.parse_args()
    fleurs.use(args.set)
    context = json.loads((fleurs.DIR / "context.json").read_text(encoding="utf-8"))["brands"]
    decoy = decoys(context)
    if args.decoys:
        for n, d in sorted(decoy.items()):
            print(f"{n} -> {d}  ({similarity(n, d):.2f})")
        print(f"\n{len(decoy)} of {len(context)} names have a usable sound-alike.")
        return
    rows = load(args.split)[: args.limit or None]
    said = pronunciations([n for n in context if not is_devanagari(n)])

    def transcripts(row: dict) -> dict[str, dict]:
        audio = row["audio"]
        terms, traps = clip_list(row, context, decoy)
        if args.both:  # the true names stay on the list beside their sound-alikes
            terms = list(dict.fromkeys([*terms, *context]))
        out = {name: fn(audio) for name, fn in WITNESSES.items()}
        # A long list is cut to the size OpenAI's baseline uses elsewhere: the sound-alikes plus other names,
        # never the recording's own (an earlier version of this line let them back in, which voided that row).
        rest = sorted((n for n in terms if n not in traps), key=lambda n: hashlib.sha1((row["id"] + n).encode()).hexdigest())
        # Alphabetical, as in the main test. With the sound-alikes placed first, OpenAI's feature wrote 19 of
        # 119 on the first set; where a name sits in the list changes how hard it is pushed.
        kw = sorted(terms if len(terms) <= fleurs.OPENAI_KEYWORDS else (traps + rest)[: fleurs.OPENAI_KEYWORDS])
        out["gpt-transcribe + its keyword list"] = transcribe(
            audio, "gpt-transcribe", languages=["hi"], prompt=SCRIPT, keywords=kw)
        kt = sarvam_terms(row, terms, traps)
        out["saaras-v4 + its keyword list"] = _cached(
            "stress saaras-v4 kt " + "|".join(kt), _sarvam("saaras:v4", "transcribe", kt, language="hi-IN"))(audio)
        if args.real:
            out["gpt-transcribe + the whole list"] = transcribe(audio, "gpt-transcribe", languages=["hi"], prompt=SCRIPT, keywords=sorted(terms))
            fifty = sorted(sorted(terms, key=lambda n: hashlib.sha1((row["id"] + n).encode()).hexdigest())[:50])
            out["saaras-v4 + 50 names of the list"] = _cached(
                "stress saaras-v4 kt " + "|".join(fifty), _sarvam("saaras:v4", "transcribe", fifty, language="hi-IN"))(audio)
        if args.alpha:
            az = sorted(kt)
            out["saaras-v4 + its keyword list, alphabetical"] = _cached(
                "stress saaras-v4 kt " + "|".join(az), _sarvam("saaras:v4", "transcribe", az, language="hi-IN"))(audio)
        index = ContextIndex({"brands": terms}, said)
        out["Parakh"] = run(audio, index, replace(CFG, jury=args.jury, vote=args.vote, acoustic=args.acoustic), WITNESSES)
        if args.stack:
            heard = {w: fn(audio) for w, fn in WITNESSES.items()}
            listed = sarvam_with_list(audio, {w: h["text"] for w, h in heard.items()}, index, CFG)
            out["saaras-v4 + 50 names chosen by Parakh"] = listed
            out["Parakh, stacked"] = run(audio, index, CFG, WITNESSES, heard={**heard, CFG.base: listed})
        return out

    with ThreadPoolExecutor(max_workers=3) as pool:  # Sarvam calls are throttled inside the adapter
        outputs = list(pool.map(transcripts, rows))

    scored: dict[str, list[dict]] = {}
    for row, outs in zip(rows, outputs):
        terms, traps = clip_list(row, context, decoy)
        for name, o in outs.items():
            text = o["text"].replace("\n", " ")
            s = score_clip(row["ref"], text, [[n, said[n]] if n in said else [n] for n in row["names"]], [], terms)
            s.update(id=row["id"], hyp=text, traps=traps, decoys_written=false_insertions(row["ref"], text, traps),
                     extra_passes=o.get("trace", {}).get("extra_passes", 0), edits=o.get("trace", {}).get("edits", []),
                     unresolved=o.get("trace", {}).get("unresolved", []), acoustic=o.get("trace", {}).get("acoustic", []))
            scored.setdefault(name, []).append(s)

    summary = {name: {**aggregate(ss), "decoys_written": sum(len(s["decoys_written"]) for s in ss)} for name, ss in scored.items()}
    n_traps = sum(len(s["traps"]) for s in scored["Parakh"])
    if args.both:
        asked = sum(len(s.get("unresolved", [])) for s in scored["Parakh"])
        print(f"sound-alike groups left as a question by Parakh: {asked}")
    table = ["| System | Sound-alikes written | Any list name written but not said | True names still right | WER |", "|---|---|---|---|---|"]
    for name in sorted(summary, key=lambda n: (summary[n]["decoys_written"], summary[n]["false_insertions"], -(summary[n]["entity_acc"] or 0))):
        a = summary[name]
        table.append(f"| {name} | {a['decoys_written']} of {n_traps} | {a['false_insertions']} | {100 * a['entity_acc']:.1f}% | {100 * a['wer']:.1f}% |")
    minutes = sum(r["duration"] for r in rows) / 60
    head = (f"Sound-alike stress test, FLEURS Hindi {args.split} split: {len(rows)} utterances, {minutes:.1f} min, "
            f"{summary['Parakh']['entity_n']} name mentions. Each recording's own names were removed from the list and "
            f"{n_traps} sound-alikes put in. Parakh made {sum(s['extra_passes'] for s in scored['Parakh'])} extra listens.")
    lines = []
    for other in ("gpt-transcribe + its keyword list", "saaras-v4 + its keyword list", "saaras-v4"):
        d, lo, hi = paired_bootstrap(scored["Parakh"], scored[other], lambda rs: sum(len(r["decoys_written"]) for r in rs) / max(1, len(rs)))
        lines.append(f"Parakh minus {other}, sound-alikes written per recording: {d:+.3f} (95% interval {lo:+.3f} to {hi:+.3f})")
    print(f"\n{head}\n\n" + "\n".join(table) + "\n\n" + "\n".join(lines))
    RUNS_DIR.mkdir(exist_ok=True)
    stem = f"stress-{args.split}" + ("-both" if args.both else "") + ("-acoustic" if args.acoustic else "") + ("-alpha" if args.alpha else "") + ("-real" if args.real else "") + (f"-jury{args.jury}" if args.jury else "") + (f"-vote{args.vote.replace('+', 'plus')}" if args.vote else "") + ("-stack" if args.stack else "")
    (RUNS_DIR / f"{stem}.md").write_text(head + "\n\n" + "\n".join(table) + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    (RUNS_DIR / f"{stem}.json").write_text(
        json.dumps({"summary": summary, "traps": n_traps, "clips": scored}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
