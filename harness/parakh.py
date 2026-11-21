"""Parakh: personal context may change a transcript only when the audio backs it.

    witnesses   two or three recognisers transcribe with no hints
    shortlist   words that sound like something in the user's context pull in the few
                closest contacts, places and brands
    hearing     one more pass listens again with that shortlist as hints, and with
                rival spellings (what the witnesses actually wrote) given equal standing
    verdict     a context name is written into the base transcript only if the hinted
                pass still chose it; everything else in the base stays untouched
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path

from harness.asr import transcribe
from harness.context import ContextIndex, Term, common_word_keys
from harness.numbers import _word_value, fmt, numbers_in
from harness.phonetic import is_devanagari, key, key_similarity, romanize, same_sound, similarity, skeleton
from harness.score import normalize, title_variants
from harness.systems import SystemFn, available_systems

PUNCT = ".,!?;:\"'()[]{}।॥…-–—"
FLOOR_MULTI = 0.70  # how alike a multi-word phrase and a context term must sound to be considered
FLOOR_SINGLE = 0.80  # single words collide by chance more easily
DISPUTED_DISCOUNT = 0.12  # where the recognisers disagree, something unusual was said: look further afield
FLOOR_ECHO = 0.62  # a second mention of an accepted name may be garbled differently
FLOOR_BACKING = 0.60  # how alike another recogniser's version must sound to count as backing a name
MAX_HINTS = 8


@dataclass
class Config:
    name: str = "parakh"
    base: str = "saaras-v4 translit"
    witnesses: tuple[str, ...] = ("saaras-v4 translit", "saaras-v3 translit", "gpt-transcribe + hi/en")
    rivals: bool = True  # offer the witnesses' own spellings as competing hints
    languages: tuple[str, ...] = ("hi", "en")  # language hint for the hearing passes
    prompt: str | None = None  # style instruction for the hearing passes, e.g. which script to write
    write_spoken: bool = False  # write a name in Devanagari (as it is said) instead of its saved spelling
    # With no context given: accept a name the topic search proposed even if no recogniser wrote it
    # unprompted, provided at least two of three hinted listens (hints in three orders) write it.
    accept_by_vote: bool = False
    # The second listen as a jury of three, each pushed a different way: the usual one (names first), the
    # same model with what was heard placed first, and Sarvam's model given the names as its keyword list.
    # A name nobody wrote unprompted is accepted only if at least this many of the three write it. 0: the
    # usual listen alone decides.
    jury: int = 0
    # Use the vendors' own keyword features as votes, given only what a product has: OpenAI gets the whole
    # name list, Sarvam the 50 names that sound most like what was heard. A name no recogniser wrote
    # unprompted is then written only by this rule. "" = off; "2of3" = any two of the usual second listen,
    # OpenAI-with-the-list and Sarvam-with-the-retrieved-list; "openai+1" = OpenAI-with-the-list and one other.
    vote: str = ""
    sarvam_mode: str = "translit"  # how the Sarvam juror is asked to write: as the base does
    sarvam_language: str = "unknown"
    # Tried and left off: letting two agreeing recognisers outvote the base on a name-like word, with no
    # context. On held-out FLEURS it fixed no names and added word errors (5.8% -> 6.0%).
    consensus: bool = False


@dataclass
class Mention:
    start: int
    end: int
    text: str
    candidates: list[tuple[Term, float]] = field(default_factory=list)


def _clean(tok: str) -> str:
    return tok.strip(PUNCT)


def find_mentions(text: str, index: ContextIndex, disputed: frozenset[int] = frozenset()) -> list[Mention]:
    """Runs of 1-4 words that sound like something in the context, best match first, no overlaps.

    disputed: positions of words the other recognisers heard differently; the bar is lower there.
    """
    clean = [_clean(t) for t in text.split()]
    found = []
    for size in range(1, 5):
        for i in range(len(clean) - size + 1):
            phrase = " ".join(c for c in clean[i : i + size] if c)
            pk = key(phrase)
            if not pk:
                continue
            if all(k in common_word_keys() for k in pk.split()) and normalize(phrase) not in index.exact:
                continue  # everyday words are never treated as a mishearing of a name
            floor = FLOOR_SINGLE if size == 1 else FLOOR_MULTI
            if not disputed.isdisjoint(range(i, i + size)):
                floor -= DISPUTED_DISCOUNT
            cands = [
                (t, s)
                for t, s in index.nearest(phrase, limit=4, floor=floor)
                if abs(len(t.keys[0].split()) - size) <= 1
            ]
            if cands:
                found.append(Mention(i, i + size, phrase, cands))
    found.sort(key=lambda m: (-m.candidates[0][1], -(m.end - m.start)))
    chosen, used = [], set()
    for m in found:
        span = set(range(m.start, m.end))
        if used.isdisjoint(span):
            chosen.append(m)
            used |= span
    return sorted(chosen, key=lambda m: m.start)


def _roman_title(phrase: str) -> str:
    return " ".join(romanize(w).capitalize() if is_devanagari(w) else w for w in phrase.split())


def _variants(term: Term) -> list[str]:
    """Every way the term may be written: its spelling, a title variant, and how it is said."""
    return [*title_variants(term.text), *term.spoken]


def align(a: list[str], b: list[str], gap: float = 0.6) -> list[tuple[int | None, int | None]]:
    """Global alignment of two token-key lists; similar-sounding tokens pair up."""
    n, m = len(a), len(b)
    cost = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i * gap
    for j in range(1, m + 1):
        cost[0][j] = j * gap
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub = 1.0 - key_similarity(a[i - 1], b[j - 1])
            cost[i][j] = min(cost[i - 1][j - 1] + sub, cost[i - 1][j] + gap, cost[i][j - 1] + gap)
    pairs, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and abs(cost[i][j] - (cost[i - 1][j - 1] + 1.0 - key_similarity(a[i - 1], b[j - 1]))) < 1e-9:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and abs(cost[i][j] - (cost[i - 1][j] + gap)) < 1e-9:
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1
    return pairs[::-1]


def _token_key(tok: str) -> str:
    return key(_clean(tok)) or _clean(tok).lower()


def _find_terms(tokens: list[str], term: Term, exact: bool = False) -> list[tuple[int, int]]:
    """Every place the term sits in a token list.

    exact=True: only the spelling the user saved (or its title variant).
    Otherwise any accepted spelling or script that is the same sound.
    """
    n = len(term.text.split())
    spans: list[tuple[int, int]] = []
    for size in sorted({max(1, n - 1), n, n + 1}, key=lambda s: abs(s - n)):
        for i in range(len(tokens) - size + 1):
            if any(a < i + size and i < b for a, b in spans):
                continue
            window = " ".join(_clean(t) for t in tokens[i : i + size])
            if exact:
                hit = any(normalize(window) == normalize(v) for v in title_variants(term.text))
            else:
                # Same consonants in the same order; a long name tolerates more vowel drift than a short one.
                floor = 0.85 if len(skeleton(term.text)) < 4 else 0.75
                hit = any(same_sound(window, v, strict_final=True) and similarity(window, v) > floor for v in _variants(term))
            if hit:
                spans.append((i, i + size))
    return sorted(spans)


def _nearest_window(tokens: list[str], term: Term) -> float:
    """How closely the best-matching run of words in a transcript sounds like the term."""
    n = len(term.text.split())
    best = 0.0
    for size in {max(1, n - 1), n, n + 1}:
        for i in range(len(tokens) - size + 1):
            pk = key(" ".join(_clean(t) for t in tokens[i : i + size]))
            if pk:
                best = max(best, term.similarity(pk))
    return best


def _nearest_text(tokens: list[str], term: Term) -> str:
    """The run of words in a transcript that sounds most like the term: what was heard where the name would go."""
    n = len(term.text.split())
    best, words = 0.0, ""
    for size in {max(1, n - 1), n, n + 1}:
        for i in range(len(tokens) - size + 1):
            phrase = " ".join(_clean(t) for t in tokens[i : i + size])
            pk = key(phrase)
            if pk and term.similarity(pk) > best:
                best, words = term.similarity(pk), phrase
    return words


def _sarvam_juror(audio: Path, hints: list[str], cfg: Config) -> str | None:
    """Saaras v4 hearing the clip with the hints as its keyword list, or None if it cannot be asked."""
    from harness.systems import _cached, _sarvam

    try:
        name = f"juror saaras-v4 {cfg.sarvam_mode} {cfg.sarvam_language} " + "|".join(hints)
        return _cached(name, _sarvam("saaras:v4", cfg.sarvam_mode, hints, language=cfg.sarvam_language))(audio)["text"]
    except Exception:  # no key, busy, out of credit: the jury is the listens that answered
        return None


def retrieve(texts: dict[str, str], index: ContextIndex, limit: int = 50, floor: float = 0.55) -> list[str]:
    """The names that sound most like anything the recognisers wrote, best first: a per-recording keyword list.

    Every run of 1-4 words in every transcript is looked up; each name keeps its best score.
    """
    best: dict[str, float] = {}
    for text in texts.values():
        clean = [_clean(t) for t in text.split()]
        for size in range(1, 5):
            for i in range(len(clean) - size + 1):
                phrase = " ".join(c for c in clean[i : i + size] if c)
                pk = key(phrase)
                if not pk or (all(k in common_word_keys() for k in pk.split()) and normalize(phrase) not in index.exact):
                    continue
                for term, score in index.nearest(phrase, limit=5, floor=floor):
                    if term.kind != "part" and score > best.get(term.text, 0.0):
                        best[term.text] = score
    return sorted(best, key=lambda n: -best[n])[:limit]


def _list_passes(audio: Path, index: ContextIndex, texts: dict[str, str], cfg: Config) -> tuple[str | None, str | None, list[str]]:
    """OpenAI with the whole list, and Saaras v4 with the retrieved 50, side by side: (openai text, sarvam text, the 50)."""
    from harness.systems import _cached, _sarvam

    whole = sorted({t.text for t in index.terms if t.kind != "part"})
    fifty = sorted(retrieve(texts, index)) if len(whole) > 50 else whole

    def openai() -> str | None:
        try:
            return transcribe(audio, "gpt-transcribe", keywords=whole, languages=list(cfg.languages), prompt=cfg.prompt)["text"]
        except Exception:
            return None

    def sarvam() -> str | None:
        if not fifty:
            return None
        try:
            name = f"list saaras-v4 {cfg.sarvam_mode} {cfg.sarvam_language} " + "|".join(fifty)
            return _cached(name, _sarvam("saaras:v4", cfg.sarvam_mode, fifty, language=cfg.sarvam_language))(audio)["text"]
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(openai), pool.submit(sarvam)
        return a.result(), b.result(), fifty


def sarvam_with_list(audio: Path, texts: dict[str, str], index: ContextIndex, cfg: Config) -> dict:
    """Saaras v4 with its own keyword feature, given the 50 listed names that sound most like what was heard.

    Sarvam's feature takes 50 terms and works best when they hold the names actually said; Parakh picks them
    from the unbiased transcripts, which needs no knowledge of the answer.
    """
    from harness.systems import _cached, _sarvam

    whole = sorted({t.text for t in index.terms if t.kind != "part"})
    fifty = sorted(retrieve(texts, index)) if len(whole) > 50 else whole
    name = f"list saaras-v4 {cfg.sarvam_mode} {cfg.sarvam_language} " + "|".join(fifty)
    return {**_cached(name, _sarvam("saaras:v4", cfg.sarvam_mode, fifty, language=cfg.sarvam_language))(audio), "names": fifty}


def disputed_positions(texts: dict[str, str], alone: bool = False) -> dict[str, frozenset[int]]:
    """For each transcript, the word positions the other transcripts heard differently.

    alone=False: some other transcript has a different-sounding word there.
    alone=True: every other transcript does, so no second recogniser backs the word.
    """
    keys = {w: [_token_key(t) for t in text.split()] for w, text in texts.items()}
    out = {}
    for w, mine in keys.items():
        differs = [0] * len(mine)
        others = [o for o in keys if o != w]
        for other in others:
            for i, j in align(mine, keys[other]):
                if i is not None and (j is None or key_similarity(mine[i], keys[other][j]) < 0.85):
                    differs[i] += 1
        need = len(others) if alone else 1
        out[w] = frozenset(i for i, n in enumerate(differs) if others and n >= need)
    return out


def transplant(
    base: str,
    sources: list[str],
    accepted: list[Term],
    write_spoken: bool = False,
    disputed: frozenset[int] = frozenset(),
) -> tuple[str, list[dict]]:
    """Write accepted context names into the base transcript.

    sources: transcripts that may contain an accepted name (the hinted pass, the other
    recognisers); a name found there is written at the matching place in the base.
    disputed: positions in the base that no other recogniser backs. Only those can be rewritten
    as a garbled repeat of an accepted name; a word two recognisers agreed on is left alone.
    """
    base_toks = base.split()
    base_keys = [_token_key(t) for t in base_toks]
    edits: list[dict] = []
    settled: list[tuple[int, int]] = []

    def overlaps(lo: int, hi: int) -> bool:
        return any(a < hi and lo < b for a, b in (*settled, *(e["span"] for e in edits)))

    def sounds_like(lo: int, hi: int, term: Term) -> float:
        return term.similarity(key(" ".join(_clean(t) for t in base_toks[lo:hi])))

    def consider(bs: int, be: int, term: Term) -> None:
        if overlaps(bs, be) or sounds_like(bs, be, term) < 0.5:
            return
        old = " ".join(_clean(t) for t in base_toks[bs:be])
        new = term.spoken[0] if write_spoken and term.spoken else term.text
        # Tried and removed: stopping a looked-up name from respelling a word that already sounds the
        # same. In Devanagari it avoided four needless respellings on FLEURS; in Roman script it is
        # exactly the fix that is wanted ("Aichar" -> "Eicher") and cost 3 of 14 on the real calls.
        if normalize(old) != normalize(new):
            edits.append({"span": (bs, be), "from": old, "to": new, "term": term.text, "kind": term.kind, "trust": term.trust})

    by_length = sorted(accepted, key=lambda t: -len(t.text.split()))
    # 1. Where the base already has the name (same sound), that exact span is claimed: respelt the
    #    way the user saved it, or left as it is, but never widened to swallow a neighbouring word.
    for term in by_length:
        if term.kind == "part":
            continue
        for bs, be in _find_terms(base_toks, term):
            if overlaps(bs, be):
                continue
            if not write_spoken:
                consider(bs, be, term)
            if not overlaps(bs, be):
                settled.append((bs, be))
    # 2. Where another transcript has the name, write it at the matching place in the base.
    for source in sources:
        src_toks = source.split()
        spans = [(term, span) for term in by_length for span in _find_terms(src_toks, term)]
        if not spans:
            continue
        pairs = align(base_keys, [_token_key(t) for t in src_toks])
        src_to_base = {j: i for i, j in pairs if i is not None and j is not None}
        base_aligned = set(src_to_base.values())
        for term, span in spans:
            mapped = sorted(src_to_base[j] for j in range(*span) if j in src_to_base)
            if not mapped:
                continue
            bs, be = mapped[0], mapped[-1] + 1
            # The base may have split the name differently ("Dam Raju"): take in neighbouring
            # words the source had no counterpart for, when that makes the match better.
            while bs > 0 and bs - 1 not in base_aligned and sounds_like(bs - 1, be, term) > sounds_like(bs, be, term):
                bs -= 1
            while be < len(base_toks) and be not in base_aligned and sounds_like(bs, be + 1, term) > sounds_like(bs, be, term):
                be += 1
            consider(bs, be, term)
    # 3. One name per conversation: once a name is accepted, other garbled mentions of it are the same name.
    repeats = []
    for term in by_length:
        n = len(term.text.split())
        for size in {max(1, n - 1), n, n + 1}:
            for i in range(len(base_toks) - size + 1):
                if disputed.isdisjoint(range(i, i + size)):
                    continue
                pk = key(" ".join(_clean(t) for t in base_toks[i : i + size]))
                if pk and not all(k in common_word_keys() for k in pk.split()):
                    sim = sounds_like(i, i + size, term)
                    if sim >= FLOOR_ECHO:
                        repeats.append((sim, i, i + size, term))
    for _, bs, be, term in sorted(repeats, key=lambda r: -r[0]):
        consider(bs, be, term)
    edits.sort(key=lambda e: e["span"])
    return apply_edits(base, edits), edits


def _rival_groups(terms: list[Term], floor: float = 0.55) -> list[list[Term]]:
    """Context names that sound enough alike to be mistaken for one another, grouped."""
    groups: list[list[Term]] = []
    for t in terms:
        home = [g for g in groups if any(max(t.similarity(k) for k in o.keys) >= floor for o in g)]
        merged = [t] + [o for g in home for o in g]
        groups = [g for g in groups if g not in home] + [merged]
    return [g for g in groups if len(g) > 1]


HONORIFICS = {key(w) for w in ("bhai", "sahab", "saab", "ji", "madam", "sir", "bhaiya", "didi", "uncle", "aunty", "seth")}


def listen(audio: Path, cfg: Config, systems: dict[str, SystemFn]) -> tuple[dict[str, dict], list[str]]:
    """Every recogniser's unprompted transcript, in parallel. One that fails is left out, not fatal."""
    def one(w: str) -> dict | Exception:
        try:
            return systems[w](audio)
        except Exception as e:  # rate limit, outage, credits: carry on with the others
            return e

    with ThreadPoolExecutor(max_workers=len(cfg.witnesses)) as pool:
        results = list(pool.map(one, cfg.witnesses))
    heard = {w: r for w, r in zip(cfg.witnesses, results) if not isinstance(r, Exception)}
    failed = [f"{w}: {r}" for w, r in zip(cfg.witnesses, results) if isinstance(r, Exception)]
    if not heard:
        raise RuntimeError("every recogniser failed: " + "; ".join(failed))
    return heard, failed


def heard_at(texts: dict[str, str], base: str, start: int, end: int) -> dict[str, str]:
    """What each other recogniser wrote where the base transcript has words start..end."""
    keys = [_token_key(t) for t in texts[base].split()]
    out = {}
    for other, text in texts.items():
        if other == base:
            continue
        o_toks = text.split()
        pairs = align(keys, [_token_key(t) for t in o_toks])
        out[other] = " ".join(_clean(o_toks[b]) for a, b in pairs if a is not None and b is not None and start <= a < end)
    return out


def _name_like(toks: list[str], keys: list[str], p: int) -> bool:
    """A word that looks like a name rather than ordinary speech or a number."""
    word = _clean(toks[p])
    if not word or len(skeleton(word)) < 2 or any(ch.isdigit() for ch in word) or _word_value(word) is not None:
        return False
    common = keys[p] in common_word_keys()
    if is_devanagari(word):  # no capital letters to go by
        return not common
    if not word[:1].isupper():
        return False  # Roman-script recognisers capitalise names
    starts_sentence = p == 0 or toks[p - 1].rstrip()[-1:] in ".?!।"
    return not (starts_sentence and common)


def unsure_spans(texts: dict[str, str], base: str, taken: list[tuple[int, int]]) -> list[dict]:
    """Name-like words in the base transcript that no other recogniser backs.

    These are shown as questions, never guessed: {"span": (start, end), "text", "heard": {recogniser: words}}.
    Kept sparing on purpose: flagging many words makes people ignore the flags.
    """
    if len(texts) < 2:
        return []
    toks = texts[base].split()
    keys = [_token_key(t) for t in toks]
    alone = disputed_positions(texts, alone=True)[base]
    out, i = [], 0
    while i < len(toks):
        if i not in alone or not _name_like(toks, keys, i):
            i += 1
            continue
        j = i + 1
        while j < len(toks) and j in alone and j - i < 3 and _name_like(toks, keys, j):
            j += 1
        end = j + 1 if j < len(toks) and keys[j] in HONORIFICS else j
        if not any(a < end and i < b for a, b in taken):
            out.append({"span": (i, end), "name": (i, j), "text": " ".join(_clean(t) for t in toks[i:end]),
                        "heard": heard_at(texts, base, i, j)})
        i = j
    return out


_TIMES = {"into", "guna", "gunaa", "x", "×", "times", "multiplied", "गुना", "इंटू"}


def products_said(texts: dict[str, str]) -> dict[float, str]:
    """Products the speakers worked out aloud: "chaalis into chaar" -> {160: "40 × 4"}."""
    out: dict[float, str] = {}
    for text in texts.values():
        nums = numbers_in(text)
        toks = [t.strip(PUNCT).lower() for t in text.split()]
        for a, b in zip(nums, nums[1:]):
            between = toks[a["end"] : b["start"]]
            if 1 <= len(between) <= 2 and between[0] in _TIMES:
                out.setdefault(a["value"] * b["value"], f"{fmt(a['value'])} × {fmt(b['value'])}")
    return out


def _by_arithmetic(base_value: float, rivals: list[float], products: dict[float, str]) -> float | None:
    """Of the values heard at one place, the one the speakers' own multiplication supports, if exactly one."""
    candidates = {base_value, *rivals} & set(products)
    return next(iter(candidates)) if len(candidates) == 1 else None


def _numbers_by_place(texts: dict[str, str], base: str):
    """For each number in the base: (number, {recogniser: [values heard at the same place]})."""
    base_toks = texts[base].split()
    keys = [_token_key(t) for t in base_toks]
    others = {}
    for other, text in texts.items():
        if other != base:
            toks = text.split()
            others[other] = (align(keys, [_token_key(t) for t in toks]), numbers_in(text))
    for n in numbers_in(texts[base]):
        heard: dict[str, list[dict]] = {}
        for other, (pairs, theirs) in others.items():
            at = [j for i, j in pairs if i is not None and j is not None and n["start"] - 1 <= i <= n["end"]]
            heard[other] = [m for m in theirs if at and m["start"] <= max(at) and min(at) < m["end"]] if at else []
        yield n, heard


def number_fixes(texts: dict[str, str], base: str, taken: list[tuple[int, int]] = (), nearby: list[str] = ()) -> list[dict]:
    """Numbers the base alone got wrong, by the other recognisers' agreement or by the speakers' own arithmetic.

    Written only when (a) every other recogniser heard the same other value at that place, or (b) the base
    disagrees with another recogniser and exactly one of the values is a product the speakers said aloud
    ("chaalis into chaar" settles 160 against 360). An agreed number is never touched. Measured on 275
    numbers in public recordings: 4 real base errors, 2 fixed by (a), none introduced.
    """
    if len(texts) < 2:
        return []
    products = products_said({**texts, **{f"nearby{i}": x for i, x in enumerate(nearby)}})
    out = []
    for n, heard in _numbers_by_place(texts, base):
        if any(a < n["end"] and n["start"] < b for a, b in taken):
            continue
        values = [m["value"] for ms in heard.values() for m in ms]
        if not values or n["value"] in values:
            continue
        others = [ms[0]["value"] for ms in heard.values() if ms]
        why, pick = None, None
        if len(others) == len(heard) and len(set(others)) == 1 and len(others) >= 2:
            pick, why = others[0], "both other recognisers heard this number"
        else:
            settled = _by_arithmetic(n["value"], values, products)
            if settled is not None and settled != n["value"]:
                pick, why = settled, f"{products[settled]} = {fmt(settled)}, as worked out in the call"
        if pick is None:
            continue
        out.append({"span": (n["start"], n["end"]), "from": n["text"], "to": fmt(pick), "term": fmt(pick), "kind": "number",
                    "trust": "recognisers", "why": why,
                    "heard": {w: ", ".join(m["text"] for m in ms) for w, ms in heard.items() if ms}})
    return out


def number_doubts(texts: dict[str, str], base: str, taken: list[tuple[int, int]] = (), nearby: list[str] = (),
                  checks: list[dict] | None = None) -> list[dict]:
    """Numbers in the base transcript that no other recogniser heard as the same number, while one heard another.

    A wrong quantity or rate costs as much as a wrong name, so these are asked about too, never settled
    by a guess. Shaped like unsure_spans, plus "value" (the base's number as digits) and "options"
    (every number heard there, the base's first). Numbers are compared by value, however they are
    written: "paanch hazaar chhe sau", "5600" and "पाँच हजार छह सौ" agree.
    """
    if len(texts) < 2:
        return []
    products = products_said({**texts, **{f"nearby{i}": x for i, x in enumerate(nearby)}})
    out = []
    for n, by_place in _numbers_by_place(texts, base):
        if any(a < n["end"] and n["start"] < b for a, b in taken):
            continue
        backed, rivals, heard = False, [], {}
        for other, near in by_place.items():
            if any(m["value"] == n["value"] for m in near):
                backed = True
                break
            if near:
                rivals += [m["value"] for m in near]
                heard[other] = ", ".join(m["text"] for m in near)
        if backed or not rivals:
            continue
        if _by_arithmetic(n["value"], rivals, products) == n["value"]:  # the speakers' own arithmetic says the base is right
            if checks is not None:
                checks.append({"span": (n["start"], n["end"]), "value": fmt(n["value"]), "heard": heard,
                               "why": f"{products[n['value']]} = {fmt(n['value'])}, as worked out in the call"})
            continue
        options = list(dict.fromkeys([n["value"], *sorted(rivals, key=lambda v: -rivals.count(v))]))
        out.append({"span": (n["start"], n["end"]), "name": (n["start"], n["end"]), "kind": "number", "text": n["text"],
                    "value": fmt(n["value"]), "options": [fmt(v) for v in options], "heard": heard})
    return out


def consensus(texts: dict[str, str], base: str, unsure: list[dict]) -> tuple[list[dict], list[dict]]:
    """Settle unsure words by majority, with no context: (edits, still unsure).

    The base wrote a name-like word nobody else backs. If the other recognisers (two or more)
    wrote the same sound as each other, their version is written instead. This only ever picks
    among words a recogniser actually wrote.
    """
    base_toks = texts[base].split()
    roman_base = not is_devanagari(texts[base])
    edits, still = [], []
    for u in unsure:
        versions = list(u["heard"].values())
        agreed = len(versions) >= 2 and all(versions) and all(same_sound(versions[0], v, strict_final=True) for v in versions[1:])
        if agreed:
            pick = next((v for v in versions if is_devanagari(v) != roman_base), versions[0])  # the base's script if possible
            if roman_base and is_devanagari(pick):
                pick = _roman_title(pick)
            i, j = u["name"]
            old = " ".join(_clean(t) for t in base_toks[i:j])
            if normalize(old) != normalize(pick):
                edits.append({"span": (i, j), "from": old, "to": pick, "term": pick, "kind": "consensus",
                              "trust": "recognisers", "heard": u["heard"]})
                continue
        still.append(u)
    return edits, still


def apply_edits(base: str, edits: list[dict]) -> str:
    """The base transcript with each edit's span replaced, keeping trailing punctuation."""
    toks = base.split()
    for e in sorted(edits, key=lambda e: -e["span"][0]):
        bs, be = e["span"]
        tail = re.search(rf"[{re.escape(PUNCT)}]+$", toks[be - 1])
        toks[bs:be] = [e["to"] + (tail.group(0) if tail else "")]
    return " ".join(toks)


def run(audio: Path, index: ContextIndex, cfg: Config, systems: dict[str, SystemFn], heard: dict | None = None,
        nearby: list[str] = ()) -> dict:
    """heard: transcripts from listen(), if the caller already has them.
    nearby: transcripts of the rest of the same call; arithmetic said there ("chaalis into chaar") can settle a number here."""
    failed: list[str] = []
    if heard is None:
        heard, failed = listen(audio, cfg, systems)
    base_name = cfg.base if cfg.base in heard else next(iter(heard))  # the usual base may be down
    cfg = replace(cfg, base=base_name)
    base = heard[cfg.base]["text"]
    latency = max(h["latency_s"] for h in heard.values())  # witnesses run in parallel

    disputed = disputed_positions({w: h["text"] for w, h in heard.items()})
    mentions = {w: find_mentions(h["text"], index, disputed[w]) for w, h in heard.items()}
    best: dict[str, tuple[Term, float]] = {}

    def consider(term: Term, sim: float) -> None:
        if term.text not in best or sim > best[term.text][1]:
            best[term.text] = (term, sim)

    # A rival spelling is offered in the script the base writes in. Offered in Roman to a model writing
    # Devanagari it is no contest: on the sound-alike stress test "Jemi Siminoph" lost to a planted name
    # that all three recognisers had contradicted.
    words = base.split()
    spell = (lambda phrase: phrase) if sum(is_devanagari(w) for w in words) > len(words) / 2 else _roman_title
    said: dict[str, list[str]] = {}  # phonetic key of a mention -> the spellings witnesses gave it
    challenges: list[tuple[str, str]] = []  # (what a witness wrote instead, the context term it was near)
    wrote: dict[str, set[str]] = {}  # phonetic key of a mention -> the witnesses that wrote it
    for w, ms in mentions.items():
        for m in ms:
            for term, sim in m.candidates:
                consider(term, sim)
                for parent in term.parents:  # a matching first name or surname brings in the full contact
                    consider(index.by_text[parent], sim * 0.95)
            said.setdefault(key(m.text), []).append(spell(m.text))
            wrote.setdefault(key(m.text), set()).add(w)
            top = m.candidates[0][0]
            if not any(same_sound(m.text, v, strict_final=True) for v in _variants(top)):
                challenges.append((key(m.text), top.text))
    ranked = [t for t, _ in sorted(best.values(), key=lambda ts: -ts[1])]
    wrote_it = {t.text: [w for w, h in heard.items() if _find_terms(h["text"].split(), t)] for t in ranked}
    backing = {
        t.text: {w for w, h in heard.items() if _nearest_window(h["text"].split(), t) >= FLOOR_BACKING} | set(wrote_it[t.text])
        for t in ranked
    }
    # What the user already has outranks what a search turned up. A searched name needs two
    # recognisers to have heard something like it, and steps aside for a saved name it resembles.
    saved = [t for t in ranked if t.trust == "saved"]
    searched = [
        t for t in ranked
        if t.trust == "found"
        and (len(heard) == 1 or len(backing[t.text]) >= 2)
        and not any(max(t.similarity(k) for k in o.keys) >= 0.55 for o in saved if o.kind != "part")
    ]
    shortlist = sorted(saved + searched, key=ranked.index)[:MAX_HINTS]
    texts = {w: h["text"] for w, h in heard.items()}
    trace = {
        "base": cfg.base,
        "failed": failed,
        "witnesses": {w: h["text"] for w, h in heard.items()},
        "mentions": {w: [(m.text, [(t.text, round(s, 2)) for t, s in m.candidates]) for m in ms] for w, ms in mentions.items()},
        "shortlist": [t.text for t in shortlist],
    }
    if not shortlist:  # nothing sounds like the user's context: only the recognisers' own agreement can change a word
        agreed, unsure = consensus(texts, cfg.base, unsure_spans(texts, cfg.base, [])) if cfg.consensus else ([], unsure_spans(texts, cfg.base, []))
        agreed = sorted(agreed + number_fixes(texts, cfg.base, [tuple(e["span"]) for e in agreed], nearby), key=lambda e: e["span"])
        unsure = [u for u in unsure if not any(a < u["span"][1] and u["span"][0] < b for a, b in (tuple(e["span"]) for e in agreed))]
        checks: list[dict] = []
        doubts = number_doubts(texts, cfg.base, [tuple(e["span"]) for e in agreed] + [tuple(u["span"]) for u in unsure], nearby, checks)
        trace.update(early_exit=True, edits=agreed, extra_passes=0, unsure_spans=unsure, number_doubts=doubts, number_checks=checks)
        return {"text": apply_edits(base, agreed), "latency_s": latency, "cached": False, "trace": trace}

    # Corroborated: some recogniser wrote this context name on its own, with no hint, and a second
    # one heard something that at least sounds like it. One recogniser alone can make a name up
    # ("HDFC Bank" for a garbled tile name).
    corroborated = {
        t.text for t in shortlist if wrote_it[t.text] and (len(heard) == 1 or len(backing[t.text]) >= 2)
    }
    hints = [t.text for t in shortlist]
    rivals: dict[str, str] = {}
    if cfg.rivals:
        # Cross-examination. A context name nobody wrote unprompted has to beat what the
        # recognisers did write, when two of them independently wrote the same thing.
        for k, near in challenges:
            if near not in corroborated and len(wrote[k]) >= 2 and all(k not in t.keys for t in shortlist):
                rivals.setdefault(k, said[k][0])
        hints += list(rivals.values())
    # A corroborated name needs no further listening. The rest get one more pass that hears the
    # clip again with the shortlist (and any rivals) as hints.
    hinted_text, hearing_latency = None, 0.0
    jurors: list[str] = []
    accepted = [t for t in shortlist if t.text in corroborated]
    open_names = [t for t in shortlist if t.text not in corroborated]
    if open_names:
        def usual() -> dict:
            return transcribe(audio, "gpt-transcribe", keywords=hints, languages=list(cfg.languages), prompt=cfg.prompt)

        if not cfg.jury:
            hinted = usual()
            hinted_text, hearing_latency = hinted["text"], hinted["latency_s"]
            accepted += [t for t in shortlist if t not in accepted and _find_terms(hinted_text.split(), t)]
        else:
            # Where a name sits in a hint list changes how hard it is pushed. So the same question is put
            # three ways, side by side, and a name has to win under more than one of them.
            as_heard = [w for w in dict.fromkeys(spell(_nearest_text(base.split(), t)) for t in open_names) if w]
            heard_first = list(dict.fromkeys([*as_heard, *rivals.values(), *(t.text for t in shortlist)]))
            with ThreadPoolExecutor(max_workers=3) as pool:
                one = pool.submit(usual)
                two = pool.submit(transcribe, audio, "gpt-transcribe", keywords=heard_first, languages=list(cfg.languages), prompt=cfg.prompt)
                three = pool.submit(_sarvam_juror, audio, hints, cfg)
                hinted, flipped, vendor = one.result(), two.result(), three.result()
            hinted_text = hinted["text"]
            hearing_latency = max(hinted["latency_s"], flipped["latency_s"])
            jurors = [hinted_text, flipped["text"], *([vendor] if vendor else [])]
            need = min(cfg.jury, len(jurors))
            accepted += [t for t in shortlist if t not in accepted and sum(bool(_find_terms(x.split(), t)) for x in jurors) >= need]

    def hear_again() -> tuple[list[str], float]:
        """Two more hinted listens with the hints in other orders, side by side. (texts, the slower one's seconds)"""
        orders = [hints[k:] + hints[:k] for k in (1 % len(hints), 2 % len(hints))]
        with ThreadPoolExecutor(max_workers=2) as pool:
            again = list(pool.map(lambda order: transcribe(
                audio, "gpt-transcribe", keywords=order, languages=list(cfg.languages), prompt=cfg.prompt), orders))
        return [a["text"] for a in again], max(a["latency_s"] for a in again)

    # Second cross-examination. When sound-alike context names compete and no recogniser wrote
    # any of them unprompted, one hinted pass proves little: it may just echo a hint. Hear the
    # clip twice more with the hints in a different order, and keep a name only if it wins clearly.
    votes: dict[str, int] = {}
    unresolved: list[list[str]] = []
    if cfg.rivals:
        rejected: set[str] = set()
        for group in _rival_groups([t for t in shortlist if t.kind != "part"]):
            backed = [t for t in group if t.text in corroborated]
            if len(backed) == 1:  # an unprompted witness settles it
                rejected |= {t.text for t in group if t is not backed[0]}
                continue
            if backed or hinted_text is None or not any(t in accepted for t in group):
                continue
            if not votes:
                more, slowest = hear_again()
                passes = [hinted_text, *more]
                hearing_latency += slowest  # after the first hinted pass; the two run side by side
                votes = {t.text: sum(len(_find_terms(x.split(), t)) for x in passes) for t in shortlist}
            ranked = sorted(group, key=lambda t: -votes[t.text])
            top, second = votes[ranked[0].text], votes[ranked[1].text]
            if top >= 2 and top >= 2 * max(second, 1):
                rejected |= {t.text for t in ranked[1:]}
                if ranked[0] not in accepted:
                    accepted.append(ranked[0])
            else:  # no clear winner: refuse to guess
                rejected |= {t.text for t in group}
                unresolved.append([t.text for t in ranked if votes[t.text]])
        # A first name or surname goes the way of the full names it belongs to.
        accepted = [
            t for t in accepted
            if t.text not in rejected and not (t.kind == "part" and t.parents and all(p in rejected for p in t.parents))
        ]

    # A name that discovery proposed, and no recogniser wrote unprompted, is only a suggestion...
    suggested = [t.text for t in accepted if t.trust == "found" and t.text not in corroborated]
    if suggested and cfg.accept_by_vote and hinted_text is not None:
        # ...unless at least two of three hinted listens write it (cross-examination by hint order).
        more, slowest = hear_again()
        passes = [hinted_text, *more]
        if not votes:
            hearing_latency += slowest
        votes = votes or {t.text: sum(len(_find_terms(x.split(), t)) for x in passes) for t in shortlist}
        by_text = {t.text: t for t in shortlist}
        backed_by_ear = [n for n in suggested if sum(bool(_find_terms(x.split(), by_text[n])) for x in passes) >= 2]
        suggested = [n for n in suggested if n not in backed_by_ear]
    accepted = [t for t in accepted if t.text not in suggested]

    list_votes: dict[str, list[bool]] = {}
    list_texts: list[str] = []
    if cfg.vote:
        with_list, with_fifty, fifty = _list_passes(audio, index, texts, cfg)
        list_texts = [x for x in (with_list, with_fifty) if x]
        hearing_latency = max(hearing_latency, 1.5)  # the two list passes run beside the second listen
        base_toks = base.split()
        # Candidates: the shortlist, and any listed name a list pass wrote where the base has something like it.
        pool = {t.text: t for t in shortlist if t.kind != "part"}
        for x in list_texts:
            for t in index.terms:
                if t.kind != "part" and t.text not in pool and _find_terms(x.split(), t) and _nearest_window(base_toks, t) >= 0.5:
                    pool[t.text] = t
        for name, t in pool.items():
            if name in corroborated or _find_terms(base_toks, t):
                continue  # written unprompted, or the base already has it: nothing to decide
            v = [bool(hinted_text and _find_terms(hinted_text.split(), t)),
                 bool(with_list and _find_terms(with_list.split(), t)),
                 bool(with_fifty and _find_terms(with_fifty.split(), t))]
            list_votes[name] = v
            ok = sum(v) >= 2 if cfg.vote == "2of3" else (v[1] and (v[0] or v[2]))
            if ok and t not in accepted:
                accepted.append(t)
            elif not ok and t in accepted:
                accepted.remove(t)
        trace["retrieved"] = fifty
        trace["list_texts"] = list_texts

    sources = (jurors or ([hinted_text] if hinted_text else [])) + list_texts + [h["text"] for w, h in heard.items() if w != cfg.base]
    unbacked = disputed_positions({w: h["text"] for w, h in heard.items()}, alone=True)[cfg.base]
    text, edits = transplant(base, sources, accepted, cfg.write_spoken, unbacked)
    for e in edits:  # the evidence shown next to each change
        e["heard"] = heard_at(texts, cfg.base, *e["span"])
    fixed_numbers = number_fixes(texts, cfg.base, [tuple(e["span"]) for e in edits], nearby)
    if fixed_numbers:
        edits = sorted(edits + fixed_numbers, key=lambda e: e["span"])
        text = apply_edits(base, edits)
    # Places already written, or already holding an accepted name, are not open questions.
    unsure = unsure_spans(
        texts, cfg.base,
        [tuple(e["span"]) for e in edits] + [sp for t in accepted for sp in _find_terms(base.split(), t)],
    )
    # A word the base wrote exactly as a name the user saved is not an open question, whatever the
    # other recognisers made of it: the person has already said who that is.
    known = [v for t in index.terms if t.trust == "saved" for v in _variants(t)]
    base_toks = base.split()
    unsure = [u for u in unsure
              if not any(same_sound(x, v, strict_final=True) for v in known
                         for x in (u["text"], " ".join(_clean(w) for w in base_toks[u["name"][0] : u["name"][1]])))]
    if cfg.consensus:
        agreed, unsure = consensus(texts, cfg.base, unsure)
        edits = sorted(edits + agreed, key=lambda e: e["span"])
        text = apply_edits(base, edits)
    trace.update(
        hints=hints, rivals=list(rivals.values()), corroborated=sorted(corroborated), hinted=hinted_text,
        extra_passes=(max(1, len(jurors)) if hinted_text else 0) + (2 if votes else 0) + len(list_texts),
        list_votes=list_votes,
        votes={k: v for k, v in votes.items() if v}, unresolved=unresolved, suggested=suggested,
        accepted=[t.text for t in accepted], found=[t.text for t in accepted if t.trust == "found"], edits=edits,
        wrote_it={t.text: wrote_it[t.text] for t in accepted},
        wrote_exactly={t.text: [w for w, h in heard.items() if _find_terms(h["text"].split(), t, exact=True)] for t in accepted},
        unsure_spans=unsure,
        number_doubts=number_doubts(texts, cfg.base, [tuple(e["span"]) for e in edits] + [tuple(u["span"]) for u in unsure], nearby, checks := []),
        number_checks=checks,
    )
    return {"text": text, "latency_s": round(latency + hearing_latency, 3), "cached": False, "trace": trace}


def parakh_systems(index: ContextIndex | None = None) -> dict[str, SystemFn]:
    """Parakh variants as comparison-table systems; needs the Sarvam key for its witnesses."""
    systems = available_systems()
    variants = [
        Config(name="parakh (shortlist hints)", rivals=False),
        Config(name="parakh (shortlist + rivals)", rivals=True),
    ]
    if not all(w in systems for cfg in variants for w in cfg.witnesses):
        return {}
    index = index or ContextIndex.load()
    return {cfg.name: (lambda audio, cfg=cfg: run(audio, index, cfg, systems)) for cfg in variants}
