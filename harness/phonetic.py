"""Sound-based matching of Indian names and words across Devanagari and Roman script.

key("Prathyusha") == key("Pratyusha") == key("प्रत्यूषा"): spelling habits (th/t, ee/i, w/v,
doubled letters) are folded away. similarity() is a weighted edit distance over keys in
which vowels are cheap (Hindi drops and adds short 'a' freely) and consonants are not.
skeleton() keeps consonants only, so "Mehta" and "Mehra" stay different names while
"Damaraju" and "Damiraju" count as one sound with two spellings.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from rapidfuzz.distance import Levenshtein

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_FINAL_CONSONANT = re.compile(r"[क-हक़-य़]$")
# Loanword vowels (ऑ, ॉ, ऍ, ॅ) that the ITRANS scheme has no letter for.
_LOAN_VOWELS = str.maketrans({"ऑ": "ओ", "ॉ": "ो", "ऍ": "ए", "ॅ": "े"})
# ITRANS marks for nasals, nukta letters and conjuncts, mapped to casual Roman spelling.
_ITRANS_CASUAL = [("j~n", "gy"), (".N", "n"), ("~N", "n"), ("M", "n"), (".D", "d"), ("R^i", "ri"), ("kSh", "ksh")]

_VOWELS = frozenset("aeiou")
# Roman spelling habits -> one letter per sound. Order matters.
_CONSONANT_RULES = [
    ("ksh", "ks"), ("chh", "C"), ("ch", "C"), ("sh", "s"), ("ph", "f"), ("th", "t"), ("dh", "d"),
    ("bh", "b"), ("kh", "k"), ("gh", "g"), ("jh", "j"), ("zh", "j"), ("ck", "k"),
    ("ce", "se"), ("ci", "si"), ("cy", "si"), ("q", "k"), ("w", "v"), ("z", "j"), ("x", "ks"),
    ("c", "k"), ("C", "c"),
]
_VOWEL_RULES = [
    ("aa", "a"), ("ee", "i"), ("ea", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"), ("ou", "o"),
    ("au", "o"), ("ai", "e"), ("ay", "e"), ("ey", "e"), ("ei", "e"), ("ie", "i"),
]
# Consonant pairs that recognisers and spellers confuse; substituting within a pair is half price.
_SIMILAR = {frozenset(p) for p in ("td", "pb", "bv", "fp", "fv", "kg", "mn", "sc", "jc", "rl")}


def is_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI.search(text))


_NUKTA, _VIRAMA, _ANUSVARA, _CANDRABINDU = "\u093c", "\u094d", "\u0902", "\u0901"
_NASAL_CLASS = {"ङ": "कखगघ", "ञ": "चछजझ", "ण": "टठडढ", "न": "तथदध", "म": "पफबभ"}
_HOMORGANIC = re.compile("(" + "|".join(f"{n}{_VIRAMA}(?=[{c}])" for n, c in _NASAL_CLASS.items()) + ")")
_INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")


def clean_devanagari(text: str, lenient: bool = True) -> str:
    """Bring Devanagari to one canonical form before matching or scoring.

    NFC, nukta letters split consistently, zero-width characters removed, Devanagari digits to
    ASCII. lenient also folds spelling variants: nukta dropped (ज़ = ज), chandrabindu to anusvara
    (आँख = आंख), and a nasal before a consonant of its own class to anusvara (हिन्दी = हिंदी).
    Vowel signs are never removed (the Whisper normaliser bug that inflates Hindi scores).
    """
    s = unicodedata.normalize("NFC", text)
    s = s.replace("ऩ", "न" + _NUKTA).replace("ऱ", "र" + _NUKTA).replace("ऴ", "ळ" + _NUKTA)
    s = _INVISIBLE.sub("", s)
    s = s.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    if lenient:
        s = s.replace(_NUKTA, "").replace(_CANDRABINDU, _ANUSVARA)
        s = _HOMORGANIC.sub(_ANUSVARA, s)
    return s


# Conventional Roman spellings that letter-by-letter romanisation gets wrong.
_ROMAN_EXCEPTIONS = {"सिंह": "singh"}


def romanize(token: str) -> str:
    """Devanagari token -> casual Roman ('अखिलेश' -> 'akhilesh'). Other tokens pass through."""
    if not is_devanagari(token):
        return token
    if token in _ROMAN_EXCEPTIONS:
        return _ROMAN_EXCEPTIONS[token]
    token = clean_devanagari(token).translate(_LOAN_VOWELS)
    if not is_devanagari(token):
        return token.lower()
    if len(token) > 1 and _FINAL_CONSONANT.search(token):
        token += "्"  # Hindi drops the word-final inherent vowel: add a virama
    r = transliterate(token, sanscript.DEVANAGARI, sanscript.ITRANS)
    for a, b in _ITRANS_CASUAL:
        r = r.replace(a, b)
    return r.lower()


@lru_cache(maxsize=100_000)
def _word_key(word: str) -> str:
    w = romanize(unicodedata.normalize("NFKC", word)).lower()
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return ""
    w = re.sub(r"aw(?=[^aeiou]|$)", "a", w)  # Sawhney
    w = re.sub(r"ow(?=[^aeiou]|$)", "o", w)  # Gachibowli
    for a, b in _CONSONANT_RULES:
        w = w.replace(a, b)
    for a, b in _VOWEL_RULES:
        w = w.replace(a, b)
    w = w[0] + w[1:].replace("y", "i")
    return re.sub(r"(.)\1+", r"\1", w)


def key(text: str) -> str:
    """Phonetic key of a word or phrase; words stay separated by single spaces."""
    return " ".join(k for k in (_word_key(w) for w in re.split(r"[\s\-]+", text)) if k)


def skeleton(text: str) -> str:
    """Consonants of the key, ignoring vowels, 'h' and word breaks."""
    return "".join(c for c in key(text) if c not in _VOWELS and c not in " h")


def _weight(ch: str) -> float:
    """Cost of inserting or deleting one key letter."""
    if ch == "a":
        return 0.25
    if ch in _VOWELS:
        return 0.5
    if ch == "h":
        return 0.3
    if ch == " ":
        return 0.1
    if ch in "vy":
        return 0.6
    return 1.0


def _sub(a: str, b: str) -> float:
    if a == b:
        return 0.0
    if a in _VOWELS and b in _VOWELS:
        return 0.25 if frozenset((a, b)) in (frozenset("ie"), frozenset("uo")) else 0.4
    if a in _VOWELS or b in _VOWELS or " " in (a, b):
        return 1.2
    return 0.5 if frozenset((a, b)) in _SIMILAR else 1.0


@lru_cache(maxsize=200_000)
def key_length(k: str) -> float:
    """Weighted length of a key: what it costs to insert all of it."""
    return sum(_weight(c) for c in k)


_length = key_length
_SUBS: dict[tuple[str, str], float] = {}  # substitution costs, filled as letter pairs are met


@lru_cache(maxsize=400_000)
def key_distance(a: str, b: str) -> float:
    """Weighted edit distance between two phonetic keys.

    Never less than the difference of the two weighted lengths: every edit changes the length by at
    most its own cost. ContextIndex.nearest uses that to skip names that cannot be close enough.
    """
    wb = [_weight(c) for c in b]
    prev = [0.0]
    for w in wb:
        prev.append(prev[-1] + w)
    for ca in a:
        wa = _weight(ca)
        left = prev[0] + wa
        cur = [left]
        for j, cb in enumerate(b):
            if ca == cb:
                swap = prev[j]
            else:
                cost = _SUBS.get((ca, cb))
                if cost is None:
                    cost = _SUBS[(ca, cb)] = _sub(ca, cb)
                swap = prev[j] + cost
            left = min(prev[j + 1] + wa, left + wb[j], swap)
            cur.append(left)
        prev = cur
    return prev[-1]


@lru_cache(maxsize=400_000)
def key_similarity(a: str, b: str) -> float:
    """1.0 = same sound, 0.0 = nothing in common. Takes phonetic keys."""
    longest = max(_length(a), _length(b))
    return 1.0 if longest == 0 else max(0.0, 1.0 - key_distance(a, b) / longest)


@lru_cache(maxsize=200_000)
def _hard(k: str) -> str:
    """The key's consonants as one string: no vowels, no 'h', no word breaks."""
    return "".join(c for c in k if c not in _VOWELS and c not in " h")


@lru_cache(maxsize=400_000)
def similarity_at_least(a: str, b: str, floor: float) -> float:
    """key_similarity(a, b) when it reaches `floor`, otherwise 0.0, usually without the full distance.

    Three exact shortcuts, each a lower bound on the distance: the difference of the weighted
    lengths; half the plain edit distance between the consonant strings (any edit that changes a
    consonant costs at least 0.5); and stopping the table as soon as a whole row is past the limit.
    """
    la, lb = key_length(a), key_length(b)
    longest = max(la, lb)
    if longest == 0:
        return 1.0
    limit = (1.0 - floor) * longest + 1e-9
    if abs(la - lb) > limit:
        return 0.0
    if 0.5 * Levenshtein.distance(_hard(a), _hard(b), score_cutoff=int(limit / 0.5) + 1) > limit:
        return 0.0
    wb = [_weight(c) for c in b]
    prev = [0.0]
    for w in wb:
        prev.append(prev[-1] + w)
    for ca in a:  # the same table as key_distance, row by row
        wa = _weight(ca)
        left = prev[0] + wa
        cur = [left]
        for j, cb in enumerate(b):
            if ca == cb:
                swap = prev[j]
            else:
                cost = _SUBS.get((ca, cb))
                if cost is None:
                    cost = _SUBS[(ca, cb)] = _sub(ca, cb)
                swap = prev[j] + cost
            left = min(prev[j + 1] + wa, left + wb[j], swap)
            cur.append(left)
        if min(cur) > limit:  # rows never get cheaper: the distance is past the limit
            return 0.0
        prev = cur
    return max(0.0, 1.0 - prev[-1] / longest) if prev[-1] <= limit else 0.0


def similarity(a: str, b: str) -> float:
    """Sound similarity of two words or phrases in any script."""
    return key_similarity(key(a), key(b))


def _final_sound_agrees(x: str, y: str) -> bool:
    """Both end in a consonant, or both in a compatible vowel ('Nanda' is not 'Nandy')."""
    vx, vy = x[-1] in _VOWELS, y[-1] in _VOWELS
    if vx != vy:
        return False
    return not vx or x[-1] == y[-1] or frozenset((x[-1], y[-1])) in (frozenset("ie"), frozenset("uo"))


def _consonants(k: str) -> str:
    c = "".join(ch for ch in k if ch not in _VOWELS and ch not in " h")
    return c[:-1] + "s" if c.endswith("j") else c  # a final z/j and s are one sound here: चटनीज़ is "Chutneys"


def _same_word(x: str, y: str, strict_final: bool) -> bool:
    if not x or not y or _consonants(x) != _consonants(y) or key_similarity(x, y) < 0.7:
        return False
    return not strict_final or _final_sound_agrees(x, y)


def same_sound(a: str, b: str, strict_final: bool = False) -> bool:
    """Same consonants in the same order, vowels roughly alike: a spelling variant, not a different word.

    strict_final also requires the last sound to agree, which matters for names
    (Nanda/Nandy) but would reject English silent-e words (minute/मिनट).
    """
    wa, wb = key(a).split(), key(b).split()
    ja, jb = "".join(wa), "".join(wb)
    if len(_consonants(ja)) <= 2 and key_similarity(ja, jb) < 0.85:
        return False  # short phrases collide by chance
    if len(wa) == len(wb) and len(wa) > 1:
        return all(_same_word(x, y, strict_final) for x, y in zip(wa, wb))
    return _same_word(ja, jb, strict_final)
