"""Cold start: work out what a call is about and which real-world names the garbled words could be.

No context is given. An OpenAI model reads the recognisers' transcripts of the
whole call, names the topic, and proposes real names (products, brands, vehicle
models, places) for phrases that look misheard. These are only candidates: a
proposed name is written into a transcript only if the audio check in parakh.py
backs it; otherwise it is shown as a suggestion.

Runs once per call, in the background (it takes 10-30 s), never per segment.
"""

from __future__ import annotations

import hashlib
import json

from harness.asr import client
from harness.data import ROOT

CACHE_DIR = ROOT / ".cache" / "discover"
MODEL = "gpt-5.5"
PROMPT = """You help a speech recogniser. Below are automatic transcripts of the same phone call in Hindi/Hinglish, segment by segment, from several recognisers. Any of them may be wrong, especially on names.

1. "topic": one line on what the call is about.
2. "suspects": the words or phrases that are probably a misheard proper name: a product or design name, brand, company, vehicle model or place. Look hardest where the transcripts disagree or where a phrase makes no sense. Skip ordinary words, numbers, sizes and people's first names.
3. For each suspect give "heard" (what each transcript wrote) and "candidates": up to 6 names that really exist in the real world, fit the topic, and sound like what was heard. Best guess first.
4. "people": names of people (first names, with any title or "bhai"/"sahab"/"ji") on which the transcripts disagree. Give only "heard" for each; do not guess which is right.

Reply with only JSON: {"topic": str, "suspects": [{"heard": [str], "candidates": [str]}], "people": [{"heard": [str]}]}"""


def discover(segments: list[dict[str, str]], script: str | None = None) -> dict:
    """segments: one dict per segment, recogniser name -> transcript. Returns {"topic", "suspects", "candidates"}.

    script: if given (e.g. "Devanagari"), candidates are asked for in that script.
    """
    ask = PROMPT + (f"\n\nWrite every candidate in {script} script, the way it is normally written in Hindi." if script else "")
    body = "\n\n".join(
        f"[segment {n}]\n" + "\n".join(f"{chr(65 + i)}: {text}" for i, text in enumerate(seg.values()))
        for n, seg in enumerate(segments, 1)
    )
    cache_file = CACHE_DIR / (hashlib.sha256((MODEL + ask + body).encode()).hexdigest() + ".json")
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    resp = client().chat.completions.create(
        model=MODEL,
        reasoning_effort="low",
        messages=[{"role": "system", "content": ask}, {"role": "user", "content": body}],
        response_format={"type": "json_object"},
    )
    out = json.loads(resp.choices[0].message.content or "{}")
    suspects = [s for s in out.get("suspects", []) if isinstance(s, dict) and s.get("candidates")]
    names = list(dict.fromkeys(c.strip() for s in suspects for c in s["candidates"] if isinstance(c, str) and c.strip()))
    people = [p for p in out.get("people", []) if isinstance(p, dict) and p.get("heard")]
    result = {"topic": out.get("topic", ""), "suspects": suspects, "candidates": names[:30], "people": people}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result
