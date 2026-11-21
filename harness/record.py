"""Record the manifest clips from the Mac microphone, one prompt at a time.

    uv run python -m harness.record            # only clips with no audio yet
    uv run python -m harness.record c07 c12    # (re)record specific clips

Phone recordings work too: drop them in data/audio/ named <clip id>.m4a.
"""

from __future__ import annotations

import subprocess
import sys

from harness.data import AUDIO_DIR, load_manifest


def record(path, device: str) -> None:
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "avfoundation", "-i", device,
         "-ac", "1", "-ar", "16000", str(path)],
        stdin=subprocess.PIPE,
    )
    input("    recording... press Enter to stop ")
    proc.communicate(b"q")


def main() -> None:
    wanted = set(sys.argv[1:])
    clips = load_manifest()
    todo = [c for c in clips if (c.id in wanted if wanted else not c.audio)]
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"{len(todo)} clips to record. Read each line naturally, as on a phone call.\n")

    for n, c in enumerate(todo, 1):
        while True:
            print(f"[{n}/{len(todo)}] {c.id}\n\n    {c.ref}\n")
            cmd = input("    Enter = record, s = skip, q = quit: ").strip().lower()
            if cmd == "q":
                return
            if cmd == "s":
                break
            path = AUDIO_DIR / f"{c.id}.wav"
            record(path, device=":0")
            if input("    Enter = keep, r = redo: ").strip().lower() != "r":
                break
        print()


if __name__ == "__main__":
    main()
