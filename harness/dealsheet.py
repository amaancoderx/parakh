"""The deal sheet: what was agreed on a call, pulled from the verified transcript.

An OpenAI model fills a fixed form from the corrected transcript (names already checked,
spoken numbers already digits). It may only use what the transcript says, copies names
exactly, and leaves a field empty rather than guess. Runs once per call, after the
corrections, in the background.
"""

from __future__ import annotations

import hashlib
import json

from harness.asr import client
from harness.data import ROOT

CACHE_DIR = ROOT / ".cache" / "dealsheet"
MODEL = "gpt-5.5"
PROMPT = """Below is the transcript of a phone call between small traders in India (Hindi/Hinglish). Names have been verified and spoken numbers are written as digits. Words marked [?] are ones the system was unsure of.

Fill this form using only what is said in the call. Copy names and numbers exactly as written. If something is not said, use null or an empty list; never guess. Write values in simple English, keeping names and trade words as in the transcript.

Reply with only JSON:
{
 "summary": one sentence on what the call was about,
 "people": [names of people mentioned],
 "items": [{"what": product or design name, "details": size/type/quality as said, "quantity": number with unit, "rate": price as said}],
 "transport": vehicle or delivery method as said,
 "when": delivery or payment timing as said,
 "money": amounts and what they are for,
 "next_steps": [who will do what next],
 "to_check": [things that were unclear or left open in the call]
}"""


HINDI = (
    "\n\nWrite every value in simple spoken Hindi, in Devanagari script, the way a shopkeeper would say it to another. "
    "Keep people's names, brand and product names, and all numbers exactly as they are written in the transcript "
    "(Roman letters and digits). The JSON keys stay in English."
)


def deal_sheet(transcript: str, lang: str = "en") -> dict:
    """lang: "en" for simple English, "hi" for simple Hindi in Devanagari. Names and numbers are copied either way."""
    prompt = PROMPT + (HINDI if lang == "hi" else "")
    cache_file = CACHE_DIR / (hashlib.sha256((MODEL + prompt + transcript).encode()).hexdigest() + ".json")
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    resp = client().chat.completions.create(
        model=MODEL,
        reasoning_effort="low",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": transcript}],
        response_format={"type": "json_object"},
    )
    out = json.loads(resp.choices[0].message.content or "{}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
