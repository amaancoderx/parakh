"""Parakh on FLEURS Hindi (Google, CC BY 4.0): real read speech, tested on proper names.

    uv run python scripts/prepare_fleurs.py        # tags the names in the references, once
    uv run python -m harness.fleurs --split dev
    uv run python -m harness.fleurs --split test   # final numbers only

FLEURS has no context lists, so we use the standard biasing-list protocol: the
context is every proper name in the set (about 100), which each utterance sees
whole. An utterance's own names are in there among the names of all the others.

OpenAI's keyword feature gets the full list. Sarvam's takes at most 50 terms, so it
gets the utterance's own names plus other names up to 50, which is generous to it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness.asr import transcribe
from harness.context import ContextIndex
from harness.data import ROOT
from harness.ice import SCRIPT, WITNESSES
from dataclasses import replace

from harness.discover import discover
from harness.parakh import Config, listen, run, sarvam_with_list
from harness.phonetic import is_devanagari
from harness.pronounce import pronunciations
from harness.score import aggregate, score_clip, span_hit
from harness.systems import _cached, _sarvam

SETS = {"first": "fleurs_hi", "fresh": "fleurs_hi_fresh"}  # fresh: the FLEURS test split, first run after the rules were frozen
DIR = ROOT / "data" / "external" / SETS["first"]
RUNS_DIR = ROOT / "runs"


def use(which: str) -> None:
    """Point this module at one of the two prepared sets."""
    global DIR
    DIR = ROOT / "data" / "external" / SETS[which]
CFG = Config(name="Parakh", base="saaras-v4", witnesses=("saaras-v4", "saaras-v3", "gpt-transcribe"),
             languages=("hi",), prompt=SCRIPT, sarvam_mode="transcribe", sarvam_language="hi-IN")


def phone_copy(audio: Path) -> Path:
    """The recording as a phone line carries it: 300-3400 Hz, 8 kHz, G.711 mu-law. Made once, then reused."""
    out = DIR / "wav_phone" / audio.name
    if not out.exists():
        out.parent.mkdir(exist_ok=True)
        line = out.with_suffix(".mulaw.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(audio), "-af", "highpass=f=300,lowpass=f=3400",
                        "-ar", "8000", "-ac", "1", "-c:a", "pcm_mulaw", str(line)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(line), "-ar", "16000", "-c:a", "pcm_s16le", str(out)], check=True)
        line.unlink()
    return out


def load(split: str, phone: bool = False) -> list[dict]:
    rows = [json.loads(line) for line in (DIR / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    out = []
    for r in rows:
        if split != "all" and r["split"] != split:
            continue
        audio = DIR / "wav16" / f"{r['id']}.wav"  # 16-bit copies of the float wavs FLEURS ships
        with wave.open(str(audio)) as w:
            seconds = w.getnframes() / w.getframerate()
        if seconds <= 28:  # Sarvam's REST API takes clips under 30 s
            out.append({**r, "audio": phone_copy(audio) if phone else audio, "duration": seconds})
    return out


def sarvam_terms(row: dict, context: list[str]) -> list[str]:
    """The utterance's own names first, then other names in a fixed pseudo-random order, 50 in all."""
    others = sorted((n for n in context if n not in row["names"]),
                    key=lambda n: hashlib.sha1((row["id"] + n).encode()).hexdigest())
    return (row["names"] + others)[:50]


OPENAI_KEYWORDS = 100  # the size the first set used; longer lists keep the recording's own names and fill up with others


def openai_terms(row: dict, context: list[str]) -> list[str]:
    """The whole list when it fits (the first set: unchanged), else the recording's own names plus others."""
    if len(context) <= OPENAI_KEYWORDS:
        return context
    others = sorted((n for n in context if n not in row["names"]),
                    key=lambda n: hashlib.sha1((row["id"] + n).encode()).hexdigest())
    return sorted((row["names"] + others)[:OPENAI_KEYWORDS])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="first", choices=list(SETS), help="first: the set the rules were developed against; fresh: the untouched one")
    ap.add_argument("--split", default="dev", choices=["dev", "test", "fresh", "all"])
    ap.add_argument("--limit", type=int, default=0, help="first N utterances only")
    ap.add_argument("--no-context", action="store_true", help="give no system a name list: recognisers alone")
    ap.add_argument("--discover", action="store_true", help="with --no-context: let Parakh look names up itself, then check them against the audio")
    ap.add_argument("--stack", action="store_true", help="also run Parakh on Sarvam-with-its-keyword-feature, the 50 names chosen by Parakh")
    ap.add_argument("--vote", default="", choices=["", "2of3", "openai+1"], help="use the vendors' keyword features as votes")
    ap.add_argument("--jury", type=int, default=0, help="how many of the three second listens must write a name (0: the usual single listen)")
    ap.add_argument("--real", action="store_true", help="also run the keyword features as a product could: no answer key in the list")
    ap.add_argument("--alpha", action="store_true", help="also give Sarvam its 50 terms in alphabetical order, not with the recording's own names first")
    ap.add_argument("--phone", action="store_true", help="degrade every recording to phone-line quality first (8 kHz mu-law)")
    ap.add_argument("--bases", action="store_true", help="also run Parakh on top of each of the other recognisers, as if that were the one you already use")
    args = ap.parse_args()
    use(args.set)
    rows = load(args.split, args.phone)[: args.limit or None]
    if not rows:
        raise SystemExit("No utterances. Run scripts/prepare_fleurs.py first.")
    context = json.loads((DIR / "context.json").read_text(encoding="utf-8"))["brands"]
    # A few names are in Roman letters ("NPWS"). Get how they are said, for matching and for fair
    # scoring: a system that writes एनपीडब्ल्यूएस has heard "NPWS" correctly.
    said = pronunciations([n for n in context if not is_devanagari(n)])
    index = ContextIndex({}, None) if args.no_context else ContextIndex({"brands": context}, said)

    cfg = replace(CFG, jury=args.jury, vote=args.vote)

    def transcripts(row: dict) -> dict[str, dict]:
        audio = row["audio"]
        out = {name: fn(audio) for name, fn in WITNESSES.items()}
        if not args.no_context:
            out["gpt-transcribe + its keyword list"] = transcribe(
                audio, "gpt-transcribe", languages=["hi"], prompt=SCRIPT, keywords=openai_terms(row, context))
            terms = sarvam_terms(row, context)
            out["saaras-v4 + its keyword list"] = _cached(
                "fleurs saaras-v4 kt " + "|".join(terms), _sarvam("saaras:v4", "transcribe", terms, language="hi-IN"))(audio)
            if args.alpha:  # the same 50 terms, in no telling order
                az = sorted(terms)
                out["saaras-v4 + its keyword list, alphabetical"] = _cached(
                    "fleurs saaras-v4 kt " + "|".join(az), _sarvam("saaras:v4", "transcribe", az, language="hi-IN"))(audio)
        if args.no_context and args.discover:
            heard, _ = listen(audio, CFG, WITNESSES)
            found = discover([{w: h["text"] for w, h in heard.items()}], script="Devanagari")
            own = ContextIndex({"found": found["candidates"]}, None)
            out["Parakh, own lookup"] = run(audio, own, replace(CFG, accept_by_vote=True), WITNESSES, heard=heard)
        if args.real and not args.no_context:
            # What a product can actually do: it does not know which names will be said. OpenAI takes the whole
            # list. Sarvam takes 50, so it gets 50 of the list, chosen without looking at the recording.
            out["gpt-transcribe + the whole list"] = transcribe(audio, "gpt-transcribe", languages=["hi"], prompt=SCRIPT, keywords=sorted(context))
            fifty = sorted(sorted(context, key=lambda n: hashlib.sha1((row["id"] + n).encode()).hexdigest())[:50])
            out["saaras-v4 + 50 names of the list"] = _cached(
                "fleurs saaras-v4 kt " + "|".join(fifty), _sarvam("saaras:v4", "transcribe", fifty, language="hi-IN"))(audio)
        out["Parakh"] = run(audio, index, cfg, WITNESSES)
        if args.stack and not args.no_context:
            heard = {w: fn(audio) for w, fn in WITNESSES.items()}
            listed = sarvam_with_list(audio, {w: h["text"] for w, h in heard.items()}, index, cfg)
            out["saaras-v4 + 50 names chosen by Parakh"] = listed
            out["Parakh, stacked"] = run(audio, index, cfg, WITNESSES, heard={**heard, cfg.base: listed})
        if args.bases:  # the same checks, written onto another recogniser's transcript
            for base in CFG.witnesses:
                if base != CFG.base:
                    out[f"Parakh on {base}"] = run(audio, index, replace(cfg, base=base), WITNESSES)
        return out

    with ThreadPoolExecutor(max_workers=3) as pool:  # Sarvam calls are throttled inside the adapter
        outputs = list(pool.map(transcripts, rows))

    scored: dict[str, list[dict]] = {}
    for row, outs in zip(rows, outputs):
        for name, o in outs.items():
            text = o["text"].replace("\n", " ")
            s = score_clip(row["ref"], text, [[n, said[n]] if n in said else [n] for n in row["names"]], [], context)
            s.update(id=row["id"], hyp=text, latency_s=o.get("latency_s"),
                     extra_passes=o.get("trace", {}).get("extra_passes", 0), edits=o.get("trace", {}).get("edits", []))
            scored.setdefault(name, []).append(s)

    def pct(x):
        return "n/a" if x is None else f"{100 * x:.1f}%"

    summary = {name: aggregate(ss) for name, ss in scored.items()}
    table = ["| System | Names right | List names written but not said | WER |", "|---|---|---|---|"]
    for name in sorted(summary, key=lambda n: (-(summary[n]["entity_acc"] or 0), summary[n]["false_insertions"])):
        a = summary[name]
        table.append(f"| {name} | {pct(a['entity_acc'])} | {a['false_insertions']} | {pct(a['wer'])} |")
    minutes = sum(r["duration"] for r in rows) / 60
    n_names = next(iter(summary.values()))["entity_n"]
    passes = sum(s["extra_passes"] for s in scored["Parakh, own lookup" if args.discover else "Parakh"])
    given = "no context given to any system" if args.no_context else f"context list of {len(context)} names"
    if args.phone:
        given += ", every recording degraded to phone-line quality (300-3400 Hz, 8 kHz mu-law)"
    head = (f"FLEURS Hindi, {args.split} split: {len(rows)} utterances, {minutes:.1f} min, {n_names} name mentions, "
            f"{given}. Parakh made {passes} extra listens.")
    print(f"\n{head}\n\n" + "\n".join(table))
    RUNS_DIR.mkdir(exist_ok=True)
    stem = f"fleurs-{args.split}" + ("-nocontext" if args.no_context else "") + ("-discover" if args.discover else "") + ("-bases" if args.bases else "") + ("-phone" if args.phone else "") + ("-alpha" if args.alpha else "") + ("-real" if args.real else "") + (f"-jury{args.jury}" if args.jury else "") + (f"-vote{args.vote.replace('+', 'plus')}" if args.vote else "") + ("-stack" if args.stack else "")
    if args.discover:  # names Parakh wrote that the reference does not contain
        wrong = [(e["from"], e["to"]) for sc in scored["Parakh, own lookup"] for e in sc["edits"]
                 if not span_hit([e["to"]], next(r["ref"] for r in rows if r["id"] == sc["id"]), strict=True)]
        head += f" Own lookup wrote {sum(len(sc['edits']) for sc in scored['Parakh, own lookup'])} names; {len(wrong)} are not in the reference: {wrong[:6]}"
        print(head)
    (RUNS_DIR / f"{stem}.md").write_text(head + "\n\n" + "\n".join(table) + "\n", encoding="utf-8")
    (RUNS_DIR / f"{stem}.json").write_text(
        json.dumps({"summary": summary, "clips": scored}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
