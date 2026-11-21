"""Smart dictation for Indian numbers: spoken number words to digits, by rule.

    "chhe hazaar chhe sau"            -> 6600
    "ek sau adsath" / "एक सौ अड़सठ"     -> 168
    "dhai lakh" / "two and a half lakh" -> 250000
    "saadhe saat" (as a time or count)  -> 7.5
    "nine eight double four zero"       -> "98440" (a digit string, not a quantity)

Hindi (Devanagari or Roman typing) and Indian English, with lakh and crore. Rules,
not a language model: published work on Hindi correction found models break about
as many numbers as they fix. Words are matched by sound, so "paanch", "panch" and
"पाँच" are the same word.

Conservative on purpose. Roman Hindi is ambiguous ("do" is two, "saath" is sixty or
"with", "sau" is hundred), so a lone ambiguous word is left alone; a run is converted
only when it is clearly a number.
"""

from __future__ import annotations

import re

from harness.phonetic import is_devanagari, key

_HINDI_0_99 = (
    "शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस "
    "इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस "
    "सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास "
    "इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ "
    "अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उनासी अस्सी इक्यासी "
    "बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे छियानवे "
    "सत्तानवे अट्ठानवे निन्यानवे"
).split()
# Common alternative spellings, Devanagari and Roman, that the sound key alone does not cover.
_EXTRA = {
    5: "पांच paanch panch", 6: "छः छे छै chhe che chhah chah chheh", 9: "nau no", 15: "पन्द्रह pandrah",
    18: "अट्ठारह", 19: "unnis", 40: "chalis chaalis", 42: "bayalis byalis", 50: "pachas pachaas",
    52: "baawan bawan", 60: "saath sath", 68: "adsath arsath adsat", 100: "",
}
_ENGLISH = {
    "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_MULTIPLIERS = {
    100: "सौ sau hundred", 1000: "हज़ार हजार hazaar hazar hajar thousand",
    100000: "लाख lakh lac lakhs", 10000000: "करोड़ करोड crore karod crores",
}
# Roman spellings that are also everyday words; alone, they are not read as numbers.
_AMBIGUOUS = {"do", "so", "no", "at", "car", "sat", "saath", "sath", "char", "is", "ek", "das", "to", "oh", "tin"}
_NOT_NUMBERS = {"so", "no", "at", "car", "is", "to", "oh", "tin", "de", "the", "an", "be", "bye"}  # English words whose sound matches a Hindi number
_UNITS = set(
    "rupaye rupay rupees rupee rs feet foot fit set peti petiyan kilo kg din baje minute ghante nag nang piece pieces "
    "percent box boxes ton quintal meter metre gauge रुपये रुपए फीट सेट पेटी किलो दिन बजे मिनट नग पीस".split()
)
_MEDIAL_SCHWA = re.compile(r"(?<=[aeiou][^aeiou])a(?=[^aeiou][aeiou])")
_PUNCT = ".,!?;:\"'()[]{}।॥…"


def _keys(word: str) -> set[str]:
    k = key(word)
    return {k, _MEDIAL_SCHWA.sub("", k)} - {""}


def _build() -> tuple[dict[str, int], dict[str, int]]:
    units: dict[str, int] = {}
    for n, w in enumerate(_HINDI_0_99):
        for k in _keys(w):
            units.setdefault(k, n)
    for n, words in _EXTRA.items():
        for w in words.split():
            for k in _keys(w):
                units.setdefault(k, n)
    for w, n in _ENGLISH.items():
        units.setdefault(key(w), n)
    mult: dict[str, int] = {}
    for n, words in _MULTIPLIERS.items():
        for w in words.split():
            for k in _keys(w):
                mult[k] = n
    return units, mult


_UNIT_KEYS, _MULT_KEYS = _build()
# Matched by exact spelling, not by sound: "de" (give) sounds like "dhai".
_FRACTIONS = {"सवा": 1.25, "sava": 1.25, "sawa": 1.25, "डेढ़": 1.5, "dedh": 1.5, "derh": 1.5,
              "ढाई": 2.5, "dhai": 2.5, "dhaai": 2.5, "adhai": 2.5}
_SAADHE = {"साढ़े", "saadhe", "sadhe", "sarhe", "saade"}
_PAUNE = {"पौने", "paune", "pone"}


def _word_value(tok: str) -> tuple[str, float] | None:
    """('unit'|'mult'|'frac'|'saadhe'|'paune'|'digits', value) for one token, or None."""
    t = tok.strip(_PUNCT).lower()
    if not t or t in _NOT_NUMBERS:
        return None
    if re.fullmatch(r"\d[\d,]*(\.\d+)?", t):
        return "digits", float(t.replace(",", ""))
    if t in ("saath", "sath") or tok.strip(_PUNCT) == "साठ":
        return "unit", 60
    if t in ("saat", "sat") or tok.strip(_PUNCT) == "सात":
        return "unit", 7
    if t in _SAADHE:
        return "saadhe", 0.5
    if t in _PAUNE:
        return "paune", -0.25
    if t in _FRACTIONS:
        return "frac", _FRACTIONS[t]
    k = key(t)
    for kk in (k, _MEDIAL_SCHWA.sub("", k)):
        if kk in _MULT_KEYS:
            return "mult", _MULT_KEYS[kk]
        if kk in _UNIT_KEYS:
            return "unit", _UNIT_KEYS[kk]
    return None


def _value(parts: list[tuple[str, float]]) -> float | None:
    """Value of a run of number words, Indian style: [n] crore [n] lakh [n] hazaar [n] sau [n]."""
    total, current, shift, seen = 0.0, None, 0.0, False
    for kind, v in parts:
        seen = True
        if kind == "skip":
            continue
        if kind == "plus":
            if current is None:
                return None
            current += v
        elif kind in ("saadhe", "paune"):
            shift = v
        elif kind == "frac":
            if current is not None:
                return None  # "do dedh sau" is a rough range (150 to 200), not one number
            current = v
        elif kind in ("unit", "digits"):
            if current is not None and kind == "unit" and current >= 20 and current % 10 == 0 and v < 10:
                current += v  # English "forty two"
            elif current is not None and current >= 100 and current % 100 == 0 and v < 100:
                current += v  # "ek sau" then "adsath"
            elif current is None:
                current = v
            else:
                return None  # two bare numbers in a row ("chaar paanch"): a digit string or a range
            if shift:
                current += shift
                shift = 0.0
        elif kind == "mult":
            base = 1.0 if current is None else current
            if shift:
                base += shift
                shift = 0.0
            if v == 100:
                if base >= 100:
                    return None  # "aath sau aath sau" is two numbers, not one
                current = base * 100
            else:
                total += base * v
                current = None
    if not seen or shift:
        return None
    return total + (current or 0.0)


def _is_ambiguous(tok: str) -> bool:
    t = tok.strip(_PUNCT).lower()
    return not is_devanagari(t) and (t in _AMBIGUOUS or key(t) in {key(a) for a in _AMBIGUOUS})


def _split(vals: list[tuple[str, float]]) -> list[tuple[int, int]] | None:
    """Cut a run of number words into consecutive numbers ("aath sau | aath sau"), or None if it cannot be."""
    n = len(vals)
    best: list[tuple[tuple[int, int], list[tuple[int, int]]] | None] = [None] * (n + 1)
    best[n] = ((0, 0), [])
    for k in range(n - 1, -1, -1):
        for e in range(k + 1, n + 1):
            if best[e] is None or _value(vals[k:e]) is None:
                continue
            (starts_with_mult, pieces), rest = best[e]
            score = (starts_with_mult + (vals[k][0] == "mult"), pieces + 1)
            if best[k] is None or score < best[k][0]:
                best[k] = (score, [(k, e), *rest])
    return best[0][1] if best[0] else None


def find_numbers(text: str) -> list[dict]:
    """Number phrases in the text: [{"start", "end", "text", "value"}] with word positions."""
    toks = text.split()
    vals = [_word_value(t) for t in toks]
    # English "two and a half lakh": the half belongs to the number, not to the sentence.
    low = [t.strip(_PUNCT).lower() for t in toks]
    for k in range(1, len(toks) - 3):
        if low[k : k + 3] == ["and", "a", "half"] and vals[k - 1] and vals[k - 1][0] == "unit" and vals[k + 3] and vals[k + 3][0] == "mult":
            vals[k], vals[k + 1], vals[k + 2] = ("plus", 0.5), ("skip", 0.0), ("skip", 0.0)
    unit_keys = {key(u) for u in _UNITS}
    out, i = [], 0

    def wordlike(v: tuple[str, float] | None) -> bool:
        return v is not None and v[0] != "digits"

    def leads(k: int) -> bool:  # "5 hazaar", "2.5 lakh": digits straight before a multiplier belong to it
        return (vals[k] is not None and vals[k][0] == "digits" and k + 1 < len(toks) and vals[k + 1] is not None
                and vals[k + 1][0] == "mult" and toks[k].rstrip()[-1:] not in ".?!।,")

    while i < len(toks):
        if not wordlike(vals[i]) and not leads(i):
            i += 1
            continue
        j = i
        while j < len(toks) and (wordlike(vals[j]) or leads(j)):
            j += 1
            if toks[j - 1].rstrip()[-1:] in ".?!।,":  # a sentence or clause break ends the number
                break
        run = [v for v in vals[i:j] if v is not None]
        pieces = _split(run)
        found = []
        for a, b in pieces or []:
            kinds = {k for k, _ in run[a:b]}
            words = toks[i + a : i + b]
            unit_next = i + b < len(toks) and key(toks[i + b].strip(_PUNCT)) in unit_keys
            clear = (
                "mult" in kinds or bool(kinds & {"frac", "saadhe", "paune"}) or b - a >= 2
                or (not _is_ambiguous(words[0]) and unit_next)
                or (is_devanagari(words[0]) and len(words[0].strip(_PUNCT)) > 2)  # Devanagari number words are unambiguous
            )
            if not clear:  # one unclear piece ("do dedh sau", "bees baais") leaves the whole run as spoken
                found = []
                break
            found.append({"start": i + a, "end": i + b, "text": " ".join(t.strip(_PUNCT) for t in words),
                          "value": _value(run[a:b])})
        out.extend(found)
        i = max(j, i + 1)
    return out


def numbers_in(text: str) -> list[dict]:
    """Every number in the text, spoken or already written in digits, in order: [{"start", "end", "text", "value"}]."""
    found = find_numbers(text)
    taken = {i for n in found for i in range(n["start"], n["end"])}
    for i, tok in enumerate(text.split()):
        v = _word_value(tok)
        if i not in taken and v is not None and v[0] == "digits":
            found.append({"start": i, "end": i + 1, "text": tok.strip(_PUNCT), "value": v[1]})
    return sorted(found, key=lambda n: n["start"])


def fmt(value: float) -> str:
    """168 -> '168'; 7.5 -> '7.5'; 250000 -> '2,50,000' (Indian digit grouping)."""
    if value != int(value):
        return f"{value:g}"
    s = str(int(value))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])


def to_digits(text: str) -> str:
    """The text with clear number phrases written as digits; everything else untouched."""
    toks = text.split()
    for n in sorted(find_numbers(text), key=lambda n: -n["start"]):
        tail = re.search(rf"[{re.escape(_PUNCT)}]+$", toks[n["end"] - 1])
        toks[n["start"] : n["end"]] = [fmt(n["value"]) + (tail.group(0) if tail else "")]
    return " ".join(toks)
