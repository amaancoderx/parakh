"""Does the acoustic arbiter (harness/phones.py) tell true names from sound-alikes, with no vocabulary?

    uv run python -m harness.arbiter_eval --set first --split test
    uv run python -m harness.arbiter_eval --set fresh --split fresh

Three questions, all from saved transcripts plus one phone-recognition pass per clip:
  1. Discrimination: for each name said in a recording, does the true name fit the audio's phones
     better than the planted sound-alike from the stress test?
  2. No name list: where the recognisers wrote different spellings of a name, does picking the
     spelling that best fits the phones beat the base model? (The oracle picker is the ceiling.)
  3. Veto: for names Parakh wrote in the stress test (planted, so wrong) and with the true list
     (right), would "write only if the name fits the audio at least as well as what the base wrote"
     keep the right ones and block the wrong ones?
"""

from __future__ import annotations

import argparse
import json
import time

from harness import fleurs
from harness.context import ContextIndex
from harness.fleurs import CFG, load
from harness.ice import WITNESSES
from harness.parakh import _nearest_text, run
from harness.phones import fit, fold_phones, ipa_of, phones_of
from harness.phonetic import is_devanagari
from harness.pronounce import pronunciations
from harness.score import span_hit
from harness.stress import clip_list, decoys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="first", choices=list(fleurs.SETS))
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    fleurs.use(args.set)
    rows = load(args.split)[: args.limit or None]
    context = json.loads((fleurs.DIR / "context.json").read_text(encoding="utf-8"))["brands"]
    said = pronunciations([n for n in context if not is_devanagari(n)])
    decoy = decoys(context)
    say = lambda name: said.get(name, name)  # Devanagari form for the phonemiser

    t0 = time.perf_counter()
    heard_phones = {r["id"]: fold_phones(phones_of(r["audio"])) for r in rows}  # the slow part, cached after once
    print(f"phones for {len(rows)} clips in {time.perf_counter() - t0:.0f} s")

    # 1. discrimination
    pairs = right = 0
    margins = []
    for r in rows:
        ph = heard_phones[r["id"]]
        for n in r["names"]:
            d = decoy.get(n)
            if not d:
                continue
            ft, fd = fit(ipa_of(say(n)), ph), fit(ipa_of(say(d)), ph)
            pairs += 1
            right += ft < fd
            margins.append(fd - ft)
    margins.sort()
    print(f"1. true name vs planted sound-alike: arbiter picks the true name in {right} of {pairs} ({100 * right / max(1, pairs):.1f}%); "
          f"median margin {margins[len(margins) // 2]:+.3f}, worst {margins[0]:+.3f}")

    # 2. no name list: pick among the recognisers' spellings
    index = ContextIndex({"brands": context}, said)
    base_right = pick_right = oracle = mentions = changed = 0
    for r in rows:
        heard = {w: fn(r["audio"])["text"] for w, fn in WITNESSES.items()}
        ph = heard_phones[r["id"]]
        for n in r["names"]:
            term = index.by_text.get(n)
            if term is None:
                continue
            mentions += 1
            spell = {w: _nearest_text(x.split(), term) for w, x in heard.items()}
            hits = {w: span_hit([n, said[n]] if n in said else [n], x, strict=True) for w, x in heard.items()}
            base_right += hits["saaras-v4"]
            oracle += any(hits.values())
            scored = sorted(((fit(ipa_of(s), ph), w) for w, s in spell.items() if s), key=lambda x: x[0])
            if scored:
                best_w = scored[0][1]
                changed += best_w != "saaras-v4"
                pick_right += hits[best_w]
    print(f"2. no name list, {mentions} mentions: base right {base_right}, arbiter's pick right {pick_right} (changed {changed}), "
          f"any-recogniser ceiling {oracle}")

    # 3. veto on what Parakh writes
    def veto_stats(label: str, use_list: bool) -> None:
        kept_right = kept_wrong = blocked_right = blocked_wrong = 0
        for r in rows:
            terms = context if use_list else clip_list(r, context, decoy)[0]
            t = run(r["audio"], ContextIndex({"brands": terms}, said), CFG, WITNESSES)["trace"]
            ph = heard_phones[r["id"]]
            for e in t.get("edits", []):
                if e.get("kind") == "number":
                    continue
                good = span_hit([e["to"]], r["ref"], strict=True)
                f_new, f_old = fit(ipa_of(say(e["to"])), ph), fit(ipa_of(e["from"]), ph)
                keep = f_new <= f_old + 0.05
                if keep:
                    kept_right += good; kept_wrong += not good
                else:
                    blocked_right += good; blocked_wrong += not good
        print(f"3. veto, {label}: kept right {kept_right}, kept wrong {kept_wrong}, blocked right {blocked_right}, blocked wrong {blocked_wrong}")

    veto_stats("with the true list", True)
    veto_stats("planted sound-alikes", False)


if __name__ == "__main__":
    main()
