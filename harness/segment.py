"""Cut a long recording into short segments at pauses.

    uv run python -m harness.segment <recording> <output dir>

Sarvam's REST API takes clips under 30 s, and the harness works utterance by
utterance, so a real call is first split at silences into pieces of at most
MAX_SECONDS.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MAX_SECONDS = 24.0
MIN_SECONDS = 1.0


def duration(audio: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def silences(audio: Path, noise_db: int = -32, min_len: float = 0.3) -> list[tuple[float, float]]:
    """(start, end) of every pause at least min_len seconds long."""
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(audio),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_len}", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", err)]
    return list(zip(starts, ends))


def plan(total: float, pauses: list[tuple[float, float]], max_len: float = MAX_SECONDS) -> list[tuple[float, float]]:
    """Segment boundaries: cut in the middle of the last pause that keeps a piece under max_len."""
    cuts = sorted((s + e) / 2 for s, e in pauses if 0 < (s + e) / 2 < total)
    segments, start = [], 0.0
    while total - start > max_len:
        fitting = [c for c in cuts if start + MIN_SECONDS < c <= start + max_len]
        cut = fitting[-1] if fitting else start + max_len  # no pause to cut at: cut on the limit
        segments.append((start, cut))
        start = cut
    if total - start > 0.2:
        segments.append((start, total))
    return segments


def split(audio: Path, out_dir: Path, prefix: str = "seg") -> list[Path]:
    """Write 16 kHz mono wav segments and return their paths in order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for n, (start, end) in enumerate(plan(duration(audio), silences(audio)), 1):
        path = out_dir / f"{prefix}{n:02d}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(audio),
             "-ac", "1", "-ar", "16000", str(path)],
            check=True,
        )
        paths.append(path)
    return paths


if __name__ == "__main__":
    for p in split(Path(sys.argv[1]), Path(sys.argv[2])):
        print(p, f"{duration(p):.1f}s")
