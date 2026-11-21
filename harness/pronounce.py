"""How each context name is actually said, written in Devanagari.

Roman spellings do not tell you the sound: "Eicher" is said "आइशर", "JNTU" is
"जेएनटीयू". An OpenAI text model writes each name once the way an Indian speaker
pronounces it; the result is cached in data/pronunciations.json and used only
for sound matching. It never touches a transcript.
"""

from __future__ import annotations

import json

from harness.asr import client
from harness.data import ROOT

CACHE = ROOT / "data" / "pronunciations.json"
MODELS = ("gpt-5.4-mini", "gpt-4.1-mini")  # second is the fallback if the first is unavailable
PROMPT = (
    "For each name in the JSON list, write how an Indian speaker would say it aloud, in Devanagari script. "
    "Names of people, places, companies and products as they are commonly pronounced in India "
    "(Eicher -> आइशर, Paytm -> पेटीएम, Sawhney -> साहनी). Spell acronyms letter by letter "
    "(HDFC -> एचडीएफसी, JNTU -> जेएनटीयू). Keep titles (Dr -> डॉक्टर). "
    'Reply with only a JSON object mapping every input name, unchanged, to its Devanagari form.'
)


def _ask(names: list[str]) -> dict[str, str]:
    last = None
    for model in MODELS:
        try:
            resp = client().chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": PROMPT},
                          {"role": "user", "content": json.dumps(names, ensure_ascii=False)}],
                response_format={"type": "json_object"},
            )
            return json.loads(resp.choices[0].message.content or "{}")
        except Exception as e:  # try the fallback model
            last = e
    raise RuntimeError(f"pronunciation lookup failed: {last}")


def pronunciations(names: list[str], batch: int = 80) -> dict[str, str]:
    """name -> Devanagari pronunciation, asking the model only for names not cached yet."""
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    missing = [n for n in dict.fromkeys(names) if n not in cache]
    for i in range(0, len(missing), batch):
        chunk = missing[i : i + batch]
        got = _ask(chunk)
        for n in chunk:
            if isinstance(got.get(n), str) and got[n].strip():
                cache[n] = got[n].strip()
    if missing:
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return {n: cache[n] for n in names if n in cache}
