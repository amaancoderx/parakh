"""Scoring: WER, entity/format span accuracy, wrong-name insertions and an error breakdown by type.

Spans (entities, formats) are lists of accepted variants. The first variant is
the form used in the reference; any variant appearing in the hypothesis counts
as a hit, so "250000" is credited for a spoken "dhai lakh".

References are in Roman script. A system that writes Hindi in Devanagari is not
penalised for script: its Devanagari words are romanised, and they match a
reference word or name when they are the same sound (same consonants, similar
vowels). Roman-script output has to match exactly.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

import jiwer

from harness.phonetic import is_devanagari, key, romanize, same_sound

CATEGORIES = ("entity", "format", "other")
# Spelling-variant folds applied to every token, both scripts, both sides of the comparison.
_FOLDS = [("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"), ("w", "v")]


def _clean_token(tok: str) -> str:
    # Keep '.' and '@' inside email/UPI-like tokens, and '.' between digits.
    emailish = "@" in tok
    out = []
    for i, ch in enumerate(tok):
        cat = unicodedata.category(ch)
        if cat[0] in "LMN":  # letters, combining marks (Indic matras), numbers
            out.append(ch)
            continue
        prev_ok = i > 0 and tok[i - 1].isalnum()
        next_ok = i + 1 < len(tok) and tok[i + 1].isalnum()
        if ch in ".@" and emailish and prev_ok and next_ok:
            out.append(ch)
        elif ch == "." and prev_ok and next_ok and tok[i - 1].isdigit() and tok[i + 1].isdigit():
            out.append(ch)
        else:
            out.append(" ")
    return "".join(out)


def fold(token: str) -> str:
    if "@" in token:  # emails and UPI IDs must match exactly
        return token
    for a, b in _FOLDS:
        token = token.replace(a, b)
    return token


def tokens(text: str) -> list[tuple[str, bool]]:
    """Normalised tokens with a flag for those that were written in Devanagari."""
    t = unicodedata.normalize("NFKC", text).lower()
    t = re.sub(r"(?<=\d),(?=\d)", "", t)  # 2,50,000 -> 250000
    t = re.sub(r"['’]", "", t)
    t = " ".join(_clean_token(tok) for tok in t.split())
    return [(fold(romanize(tok)), is_devanagari(tok)) for tok in t.split()]


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, romanise Devanagari and fold spelling variants,
    so 'रुपये', 'rupaye' and 'rupaaye' compare equal."""
    return " ".join(tok for tok, _ in tokens(text))


def _despace(text: str) -> str:
    return text.replace(" ", "")


def _contains(hyp_toks: list[str], target: str) -> bool:
    """True if some run of whole tokens, joined without spaces, equals the target."""
    for i in range(len(hyp_toks)):
        acc = ""
        for tok in hyp_toks[i:]:
            acc += tok
            if acc == target:
                return True
            if not target.startswith(acc):
                break
    return False


def span_hit(variants: list[str], hyp: str, strict: bool = False) -> bool:
    """True if an accepted variant appears in the hypothesis as whole words.

    Exact (spacing-insensitive) for Roman-script output; same-sound for Devanagari words.
    strict=True is for names: the final sound must agree too.
    """
    hyp_toks = tokens(hyp)
    plain = [t for t, _ in hyp_toks]
    for v in variants:
        vn = normalize(v)
        if _contains(plain, _despace(vn)):
            return True
        n = len(vn.split())
        for size in {max(1, n - 1), n, n + 1}:
            for i in range(len(hyp_toks) - size + 1):
                window = hyp_toks[i : i + size]
                if any(dev for _, dev in window) and same_sound(" ".join(t for t, _ in window), vn, strict):
                    return True
    return False


def find_span(ref_tokens: list[str], span_tokens: list[str]) -> int:
    n = len(span_tokens)
    for i in range(len(ref_tokens) - n + 1):
        if ref_tokens[i : i + n] == span_tokens:
            return i
    return -1


def token_categories(ref: str, entities: list[list[str]], formats: list[list[str]]) -> list[str]:
    """Label each normalised reference token as entity / format / other."""
    toks = normalize(ref).split()
    cats = ["other"] * len(toks)
    for label, spans in (("format", formats), ("entity", entities)):  # entity wins overlaps
        for variants in spans:
            span = normalize(variants[0]).split()
            i = find_span(toks, span)
            if i >= 0:
                cats[i : i + len(span)] = [label] * len(span)
    return cats


def non_latin_share(hyp: str) -> float:
    """Share of hypothesis tokens written in a non-Latin script (e.g. Devanagari)."""
    toks = unicodedata.normalize("NFKC", hyp).split()  # raw text: normalize() romanises
    if not toks:
        return 0.0
    non_latin = sum(
        1 for t in toks if any(ch.isalpha() and "LATIN" not in unicodedata.name(ch, "") for ch in t)
    )
    return non_latin / len(toks)


def title_variants(term: str) -> list[str]:
    """'Dr Mehta' is also 'Doctor Mehta'."""
    first, _, rest = term.partition(" ")
    if rest and first.lower().rstrip(".") == "dr":
        return [term, f"Doctor {rest}"]
    return [term]


def _written(forms: list[str], text: str) -> bool:
    """The term appears as whole words: exact in Roman script, or the identical sound in Devanagari."""
    toks = tokens(text)
    plain = [t for t, _ in toks]
    for f in forms:
        fn = normalize(f)
        if _contains(plain, _despace(fn)):
            return True
        n = len(fn.split())
        for i in range(len(toks) - n + 1):
            window = toks[i : i + n]
            if any(dev for _, dev in window) and key(" ".join(t for t, _ in window)) == key(fn):
                return True
    return False


def false_insertions(ref: str, hyp: str, context_terms: list[str]) -> list[str]:
    """Context terms (contacts, places, brands) that the hypothesis contains but the reference does not.

    Stricter than span_hit on purpose, so an everyday word (अंदर) is not read as a name (Indore).
    """
    ref_joined = _despace(normalize(ref))
    out = []
    for term in context_terms:
        forms = title_variants(term)
        if not _written(forms, hyp) or span_hit(forms, ref, strict=True):
            continue
        if any(_despace(normalize(f)) in ref_joined for f in forms):
            continue  # part of a longer reference word, e.g. HDFC inside a UPI handle
        out.append(term)
    return out


def _align(ref_toks: list[tuple[str, bool]], hyp_toks: list[tuple[str, bool]]):
    """Word alignment in which a Devanagari word matches a same-sound word in the other script."""
    ref = [t for t, _ in ref_toks]
    hyp = [t for t, _ in hyp_toks]
    out = jiwer.process_words(" ".join(ref), " ".join(hyp))
    patched = list(hyp)
    for chunk in out.alignments[0]:
        if chunk.type != "substitute":
            continue
        for k in range(chunk.ref_end_idx - chunk.ref_start_idx):
            i, j = chunk.ref_start_idx + k, chunk.hyp_start_idx + k
            if (hyp_toks[j][1] or ref_toks[i][1]) and same_sound(ref[i], hyp[j]):
                patched[j] = ref[i]
    if patched == hyp:
        return out
    return jiwer.process_words(" ".join(ref), " ".join(patched))


def score_clip(
    ref: str,
    hyp: str,
    entities: list[list[str]],
    formats: list[list[str]],
    context_terms: list[str] | None = None,
) -> dict:
    ref_n, hyp_n = normalize(ref), normalize(hyp)
    cats = token_categories(ref, entities, formats)
    out = _align(tokens(ref), tokens(hyp))

    errors = Counter()
    for chunk in out.alignments[0]:
        if chunk.type in ("substitute", "delete"):
            for i in range(chunk.ref_start_idx, chunk.ref_end_idx):
                errors[cats[i]] += 1
        elif chunk.type == "insert":
            errors["insertion"] += chunk.hyp_end_idx - chunk.hyp_start_idx

    return {
        "ref_norm": ref_n,
        "hyp_norm": hyp_n,
        "ref_tokens": len(cats),
        "tokens_by_cat": dict(Counter(cats)),
        "errors_by_cat": dict(errors),
        "errors": sum(errors.values()),
        "wer": out.wer,
        "entity_hits": [span_hit(v, hyp, strict=True) for v in entities],
        "format_hits": [span_hit(v, hyp) for v in formats],
        "non_latin_share": non_latin_share(hyp),
        "false_insertions": false_insertions(ref, hyp, context_terms or []),
    }


def aggregate(rows: list[dict]) -> dict:
    """Corpus-level numbers from per-clip score_clip() results."""
    ref_tokens = sum(r["ref_tokens"] for r in rows)
    tokens_by_cat = Counter()
    errors = Counter()
    for r in rows:
        tokens_by_cat.update(r["tokens_by_cat"])
        errors.update(r["errors_by_cat"])
    ent = [h for r in rows for h in r["entity_hits"]]
    fmt = [h for r in rows for h in r["format_hits"]]

    def rate(hits):
        return sum(hits) / len(hits) if hits else None

    return {
        "clips": len(rows),
        "ref_tokens": ref_tokens,
        "wer": sum(errors.values()) / ref_tokens if ref_tokens else None,
        "entity_acc": rate(ent),
        "entity_n": len(ent),
        "format_acc": rate(fmt),
        "format_n": len(fmt),
        "errors_by_cat": {c: errors.get(c, 0) for c in (*CATEGORIES, "insertion")},
        "error_rate_by_cat": {
            c: (errors.get(c, 0) / tokens_by_cat[c] if tokens_by_cat.get(c) else None) for c in CATEGORIES
        },
        "non_latin_share": sum(r["non_latin_share"] for r in rows) / len(rows) if rows else 0.0,
        "false_insertions": sum(len(r.get("false_insertions", [])) for r in rows),
    }
