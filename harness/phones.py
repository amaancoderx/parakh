"""The acoustic arbiter: what sounds are in the audio, with no vocabulary at all.

The three recognisers are language models with a lexicon, so a rare name is pulled toward a
common word (Eicher -> Aishwarya). This channel has no lexicon: a wav2vec2 model trained to emit
IPA phones (facebook/wav2vec2-xlsr-53-espeak-cv-ft, CTC, no language model) reads the clip as a
phone string. Each candidate name is turned into IPA with espeak-ng, and the candidate whose
phones best fit somewhere in the audio's phone string wins.

    uv run python -m harness.phones <clip.wav> "आइशर" "ऐश्वर्या" "Eicher"

Everything is cached: the phone string per audio (.cache/phones/), the IPA per name.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import wave
from functools import lru_cache
from pathlib import Path

from harness.data import ROOT

CACHE_DIR = ROOT / ".cache" / "phones"
MODEL = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
_model = None
_processor = None


def _load():
    global _model, _processor
    if _model is None:
        import torch
        from transformers import AutoModelForCTC, AutoProcessor

        _processor = AutoProcessor.from_pretrained(MODEL)
        _model = AutoModelForCTC.from_pretrained(MODEL).eval()
        torch.set_num_threads(4)
        if torch.backends.mps.is_available():  # the Mac's GPU, about 5x faster than its CPU here
            try:
                _model = _model.to("mps")
            except Exception:
                pass
    return _model, _processor


def _read_wav(path: Path) -> tuple[list[float], int]:
    import numpy as np

    with wave.open(str(path)) as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1, "16-bit mono wav expected"
        rate = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float32") / 32768.0
    return pcm, rate


def phones_of(audio: Path) -> str:
    """The clip as one IPA string, phones separated by spaces (CTC greedy decode)."""
    key = hashlib.sha256(audio.read_bytes() + MODEL.encode()).hexdigest()
    cache = CACHE_DIR / f"{key}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["phones"]
    import torch
    import torchaudio.functional as F

    model, processor = _load()
    pcm, rate = _read_wav(audio)
    x = torch.tensor(pcm)
    if rate != 16000:
        x = F.resample(x, rate, 16000)
    out = []
    step = 16000 * 20  # 20 s windows, so a long clip does not exhaust memory
    for i in range(0, len(x), step):
        inputs = processor(x[i : i + step].numpy(), sampling_rate=16000, return_tensors="pt")
        device = next(model.parameters()).device
        with torch.no_grad():
            logits = model(**{k: v.to(device) for k, v in inputs.items()}).logits
        ids = torch.argmax(logits.cpu(), dim=-1)[0].tolist()
        out.append(processor.batch_decode([ids])[0])
    text = " ".join(out)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"phones": text}, ensure_ascii=False), encoding="utf-8")
    return text


@lru_cache(maxsize=10_000)
def ipa_of(name: str, language: str = "hi") -> str:
    """A name as IPA phones (espeak-ng). Roman spellings are read as Hindi too, which suits Indian names."""
    try:
        out = subprocess.run(["espeak-ng", "-v", language, "-q", "--ipa=3", name], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return _fold(out)


_DROP = str.maketrans("", "", "ˈˌːˑ̩̯̪̃̚ʲʰʷ͡ ")  # stress, length, diacritics, aspiration marks and spaces


def _fold(ipa: str) -> str:
    """One comparable phone string: stress, length and most diacritics removed, close phones merged."""
    s = ipa.replace("_", " ").translate(_DROP)
    for a, b in (("ɾ", "r"), ("ɽ", "r"), ("ʋ", "v"), ("w", "v"), ("ɛ", "e"), ("ɔ", "o"), ("ʊ", "u"), ("ɪ", "i"),
                 ("ʌ", "ə"), ("ɐ", "ə"), ("ɑ", "a"), ("æ", "e"), ("ʃ", "s"), ("ʂ", "s"), ("ɳ", "n"), ("ŋ", "n"), ("ɲ", "n"),
                 ("ʈ", "t"), ("ɖ", "d"), ("ɡ", "g"), ("dʒ", "j"), ("tʃ", "c"), ("ʒ", "j"), ("x", "k"), ("ɣ", "g"), ("q", "k"), ("θ", "t"), ("ð", "d")):
        s = s.replace(a, b)
    return re.sub(r"[^a-zəhjlmnrsvbdgkpt]", "", s)


def fold_phones(phones: str) -> str:
    return _fold(phones)


def fit(candidate_ipa: str, audio_ipa: str) -> float:
    """How well the candidate's phones fit somewhere in the audio's phones: 0 = perfect, 1 = nothing.

    Local alignment (edit distance against any substring of the audio), divided by the candidate's length.
    Vowel mismatches cost half: vowels are what speakers, channels and dialects vary most.
    """
    c, a = candidate_ipa, audio_ipa
    if not c or not a:
        return 1.0
    vowels = set("aeiouə")
    prev = [0.0] * (len(a) + 1)  # free start anywhere in the audio
    for ci in c:
        cur = [prev[0] + 1.0]
        for j, aj in enumerate(a, 1):
            sub = 0.0 if ci == aj else (0.5 if ci in vowels and aj in vowels else 1.0)
            cur.append(min(prev[j - 1] + sub, prev[j] + 1.0, cur[j - 1] + 1.0))
        prev = cur
    return min(prev) / len(c)  # free end anywhere in the audio


def arbitrate(audio: Path, candidates: dict[str, str]) -> list[tuple[str, float]]:
    """candidates: display name -> what to phonemise (Devanagari if known). Best fit first."""
    heard = fold_phones(phones_of(audio))
    scored = [(name, fit(ipa_of(say), heard)) for name, say in candidates.items()]
    return sorted(scored, key=lambda x: x[1])


if __name__ == "__main__":
    clip = Path(sys.argv[1])
    print("phones:", fold_phones(phones_of(clip))[:300])
    for name, score in arbitrate(clip, {n: n for n in sys.argv[2:]}):
        print(f"  {score:.3f}  {name}  [{ipa_of(name)}]")
