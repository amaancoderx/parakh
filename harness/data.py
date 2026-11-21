"""Manifest loading and the frozen dev/test split."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from harness.score import find_span, normalize

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.jsonl"
AUDIO_DIR = ROOT / "data" / "audio"
AUDIO_EXTS = (".wav", ".m4a", ".mp3", ".ogg", ".flac", ".webm", ".mp4")


@dataclass
class Clip:
    id: str
    ref: str
    entities: list[list[str]] = field(default_factory=list)
    formats: list[list[str]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    split: str = "dev"
    audio: Path | None = None


def split_for(clip_id: str) -> str:
    """Deterministic split from the clip id, so it cannot drift while tuning."""
    return "dev" if hashlib.sha1(clip_id.encode()).digest()[0] % 2 == 0 else "test"


def find_audio(clip_id: str, audio_dir: Path = AUDIO_DIR) -> Path | None:
    for ext in AUDIO_EXTS:
        p = audio_dir / f"{clip_id}{ext}"
        if p.exists():
            return p
    return None


def load_manifest(path: Path = MANIFEST, split: str | None = None, audio_dir: Path = AUDIO_DIR) -> list[Clip]:
    clips = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        clip = Clip(
            id=d["id"],
            ref=d["ref"],
            entities=d.get("entities", []),
            formats=d.get("formats", []),
            tags=d.get("tags", []),
            split=d.get("split") or split_for(d["id"]),
            audio=find_audio(d["id"], audio_dir),
        )
        ref_toks = normalize(clip.ref).split()
        for variants in (*clip.entities, *clip.formats):
            if find_span(ref_toks, normalize(variants[0]).split()) < 0:
                raise ValueError(f"{clip.id}: span {variants[0]!r} not found in ref")
        if split is None or clip.split == split:
            clips.append(clip)
    return clips
