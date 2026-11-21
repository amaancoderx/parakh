"""The user's personal context (contacts, places, brands) as an index searchable by sound."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz, process
from wordfreq import top_n_list

from harness.data import ROOT
from harness.phonetic import key, key_similarity, similarity_at_least, skeleton
from harness.pronounce import pronunciations
from harness.score import normalize

CONTEXT = ROOT / "data" / "context.json"
_TITLES = {"dr": "doctor", "doctor": "dr"}


@dataclass(frozen=True)
class Term:
    text: str  # canonical spelling, as saved by the user
    kind: str  # contact | place | brand | part (one word of a contact's name)
    keys: tuple[str, ...]  # phonetic keys, including title variants (Dr / Doctor)
    parents: tuple[str, ...] = ()  # for a part: the full contact names it belongs to
    spoken: tuple[str, ...] = ()  # how the name is said, in Devanagari (see pronounce.py)
    trust: str = "saved"  # saved = typed in or learned earlier; found = proposed by discovery for this call

    def similarity(self, phrase_key: str) -> float:
        return max(key_similarity(phrase_key, k) for k in self.keys)


_MEDIAL_SCHWA = re.compile(r"(?<=[aeiou][^aeiou])a(?=[^aeiou][aeiou])")


@lru_cache(maxsize=1)
def common_word_keys() -> frozenset[str]:
    """Phonetic keys of everyday Hindi and English words, which must never be 'corrected' to a name.

    Hindi words are stored with and without their medial short 'a' (उसका is typed "uska", not "usaka").
    """
    keys = set()
    for lang in ("en", "hi"):
        for w in top_n_list(lang, 5000):
            k = key(w)
            keys.add(k)
            keys.add(_MEDIAL_SCHWA.sub("", k))
    return frozenset(keys - {""})


class ContextIndex:
    def __init__(self, context: dict[str, list[str]], spoken: dict[str, str] | None = None):
        self.terms: list[Term] = []
        self._spoken = spoken or {}
        self._seen: set[tuple[str, str]] = set()
        for field, kind in (("contacts", "contact"), ("places", "place"), ("brands", "brand")):
            for text in context.get(field, []):
                self._add(text, kind)
        for text in context.get("found", []):  # discovery's candidates: used only if the audio backs them
            self._add(text, "name", trust="found")
        # Single words of multi-word contact names: a caller may share a surname with a contact.
        parents: dict[str, list[str]] = {}
        for text in context.get("contacts", []):
            words = text.split()
            if len(words) > 1:
                for w in words:
                    if len(skeleton(w)) >= 3 and key(w) not in common_word_keys():
                        parents.setdefault(w, []).append(text)
        for word, full_names in parents.items():
            self._add(word, "part", tuple(full_names))
        self._keys = [t.keys[0] for t in self.terms]
        self.by_text = {t.text: t for t in self.terms}
        self.exact = {normalize(t.text) for t in self.terms}

    def _add(self, text: str, kind: str, parents: tuple[str, ...] = (), trust: str = "saved") -> None:
        k = key(text)
        if not k or (k, kind) in self._seen or (kind in ("part", "name") and any(k == s for s, _ in self._seen)):
            return
        self._seen.add((k, kind))
        keys = [k]
        first, _, rest = text.partition(" ")
        if rest and first.lower().rstrip(".") in _TITLES:
            keys.append(key(f"{_TITLES[first.lower().rstrip('.')]} {rest}"))
        said = self._spoken.get(text)
        if said and key(said) not in keys:
            keys.append(key(said))
        self.terms.append(Term(text, kind, tuple(keys), parents, (said,) if said else (), trust))

    @classmethod
    def build(cls, context: dict[str, list[str]], pronounce: bool = True) -> "ContextIndex":
        """pronounce=True asks an OpenAI model, once per new name, how each name is said."""
        names = [t for field in ("contacts", "places", "brands", "found") for t in context.get(field, [])]
        return cls(context, pronunciations(names) if pronounce else None)

    @classmethod
    def load(cls, path: Path = CONTEXT, pronounce: bool = True) -> "ContextIndex":
        return cls.build(json.loads(path.read_text(encoding="utf-8")), pronounce)

    def nearest(self, phrase: str, limit: int = 5, floor: float = 0.6) -> list[tuple[Term, float]]:
        """Terms that sound most like the phrase, best first."""
        pk = key(phrase)
        if not pk:
            return []
        pool = self.terms
        if len(pool) > 300:  # cheap character-level prefilter before the weighted sound distance
            hits = process.extract(pk, self._keys, scorer=fuzz.ratio, limit=60)
            pool = [self.terms[i] for _, _, i in hits]
        scored = []
        for t in pool:  # most names are nowhere near the phrase: similarity_at_least rules them out cheaply
            best = max(similarity_at_least(pk, k, floor) for k in t.keys)
            if best >= floor:
                scored.append((t, best))
        scored.sort(key=lambda ts: -ts[1])
        return scored[:limit]
