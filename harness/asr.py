"""OpenAI transcription with an on-disk cache, so reruns are free and repeatable."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from harness.data import ROOT

CACHE_DIR = ROOT / ".cache" / "asr"
_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        load_dotenv(ROOT / ".env")
        _client = OpenAI()
    return _client


def transcribe(
    audio: Path,
    model: str,
    language: str | None = None,
    prompt: str | None = None,
    keywords: list[str] | None = None,
    languages: list[str] | None = None,
) -> dict:
    """Returns {"text", "latency_s", "cached"}. Latency is the original call's when cached.

    `keywords` and `languages` are only supported by gpt-transcribe.
    """
    key = hashlib.sha256(
        audio.read_bytes() + json.dumps([model, language, prompt, keywords, languages]).encode()
    ).hexdigest()
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        return {**json.loads(cache_file.read_text(encoding="utf-8")), "cached": True}

    kwargs: dict[str, Any] = {"model": model, "response_format": "json"}
    if language:
        kwargs["language"] = language
    if prompt:
        kwargs["prompt"] = prompt
    if keywords:
        kwargs["keywords"] = keywords
    if languages:
        kwargs["languages"] = languages
    t0 = time.perf_counter()
    with audio.open("rb") as f:
        resp = client().audio.transcriptions.create(file=f, **kwargs)
    result = {"text": resp.text, "latency_s": round(time.perf_counter() - t0, 3)}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return {**result, "cached": False}
