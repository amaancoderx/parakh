"""Every system in the comparison table: name -> fn(audio path) -> {"text", "latency_s", "cached"}.

OpenAI systems are always listed. Third-party recognisers are listed only when
their API key is in the environment. The Deepgram adapter is written from its
public REST docs and is unverified.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
from pathlib import Path
from typing import Callable

import httpx
from dotenv import load_dotenv

from harness.asr import transcribe
from harness.data import ROOT

load_dotenv(ROOT / ".env")

CACHE_DIR = ROOT / ".cache" / "systems"
CONTEXT = ROOT / "data" / "context.json"

SystemFn = Callable[[Path], dict]


def context_terms() -> list[str]:
    ctx = json.loads(CONTEXT.read_text(encoding="utf-8"))
    return [t for key in ("contacts", "places", "brands") for t in ctx[key]]


def _cached(name: str, fn: Callable[[Path], str]) -> SystemFn:
    """Wrap a text-returning call with timing and an on-disk cache."""

    def run(audio: Path) -> dict:
        key = hashlib.sha256(audio.read_bytes() + name.encode()).hexdigest()
        cache_file = CACHE_DIR / f"{key}.json"
        if cache_file.exists():
            return {**json.loads(cache_file.read_text(encoding="utf-8")), "cached": True}
        t0 = time.perf_counter()
        text = fn(audio)
        result = {"text": text, "latency_s": round(time.perf_counter() - t0, 3)}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return {**result, "cached": False}

    return run


def _openai(model: str, **kwargs) -> SystemFn:
    return lambda audio: transcribe(audio, model, **kwargs)


def _deepgram(audio: Path) -> str:
    r = httpx.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": os.getenv("DEEPGRAM_MODEL", "nova-3"), "language": "multi", "smart_format": "true"},
        headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}", "Content-Type": "audio/*"},
        content=audio.read_bytes(),
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["results"]["channels"][0]["alternatives"][0]["transcript"]


def _elevenlabs(model: str) -> Callable[[Path], str]:
    def call(audio: Path) -> str:
        with audio.open("rb") as f:
            r = httpx.post(
                "https://api.elevenlabs.io/v1/speech-to-text",
                headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                data={"model_id": model},
                files={"file": (audio.name, f)},
                timeout=120,
            )
        r.raise_for_status()
        return r.json()["text"]

    return call


_sarvam_lock = threading.Lock()
_sarvam_tokens = 3.0
_sarvam_stamp = time.monotonic()


def _sarvam_throttle(every: float = 1.1, burst: float = 3.0) -> None:
    """Sarvam's pay-as-you-go tier allows 60 REST requests a minute.

    A short burst goes straight through (one clip asks two Sarvam models at the same moment);
    a long batch settles at one request every 1.1 seconds.
    """
    global _sarvam_tokens, _sarvam_stamp
    while True:
        with _sarvam_lock:
            now = time.monotonic()
            _sarvam_tokens = min(burst, _sarvam_tokens + (now - _sarvam_stamp) / every)
            _sarvam_stamp = now
            if _sarvam_tokens >= 1:
                _sarvam_tokens -= 1
                return
            wait = (1 - _sarvam_tokens) * every
        time.sleep(wait)


def _sarvam(model: str, mode: str, keyterms: list[str] | None = None, language: str = "unknown") -> Callable[[Path], str]:
    """Sarvam REST speech-to-text. Clips must be under 30 s; keyterms (max 50) are saaras:v4 only."""

    def call(audio: Path) -> str:
        _sarvam_throttle()
        data = {"model": model, "mode": mode, "language_code": language}
        if keyterms:
            data["keyterms"] = json.dumps(keyterms[:50], ensure_ascii=False)
        for attempt in range(3):  # busy (429) or a server error: wait a little and ask again; anything else is final
            with audio.open("rb") as f:
                r = httpx.post(
                    "https://api.sarvam.ai/speech-to-text",
                    headers={"api-subscription-key": os.environ["SARVAM_API_KEY"]},
                    data=data,
                    files={"file": (audio.name, f)},
                    timeout=120,
                )
            if r.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                break
            time.sleep(0.7 * 2**attempt + random.random() * 0.3)
            _sarvam_throttle()
        if r.status_code >= 400:
            raise RuntimeError(f"Sarvam {r.status_code}: {r.text[:300]}")
        return r.json()["transcript"]

    return call


def available_systems() -> dict[str, SystemFn]:
    terms = context_terms()
    systems: dict[str, SystemFn] = {
        # Previous OpenAI model, deprecated (shutdown 2027-02-26); 32% OI-WER on Voice of India Hindi.
        "gpt-4o-transcribe": _openai("gpt-4o-transcribe"),
        # Current base model, and OpenAI's own built-in biasing with the full context list.
        "gpt-transcribe": _openai("gpt-transcribe"),
        "gpt-transcribe + hi/en": _openai("gpt-transcribe", languages=["hi", "en"]),
        "gpt-transcribe + keywords + hi/en": _openai("gpt-transcribe", keywords=terms, languages=["hi", "en"]),
    }
    if os.getenv("SARVAM_API_KEY"):
        # translit = Roman-script output, the mode Equal reportedly runs on Saaras v3.
        systems["saaras-v3 translit"] = _cached("saaras-v3 translit", _sarvam("saaras:v3", "translit"))
        systems["saaras-v4 translit"] = _cached("saaras-v4 translit", _sarvam("saaras:v4", "translit"))
    if os.getenv("ELEVENLABS_API_KEY"):
        systems["elevenlabs scribe-v2"] = _cached("elevenlabs scribe-v2", _elevenlabs("scribe_v2"))
    if os.getenv("DEEPGRAM_API_KEY"):
        systems["deepgram"] = _cached("deepgram", _deepgram)
    return systems
