"""Free synthetic dev audio from the macOS system voices, pushed through a phone-band filter.

    uv run python -m harness.synth

This is a DEVELOPMENT aid for building the pipeline before real recordings exist.
Numbers measured on it are not evidence for any claim: it is two clean TTS voices.
English lines use the en_IN voice; Hinglish lines use the hi_IN voice reading the
Devanagari rendering below.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from harness.data import ROOT, load_manifest

SYNTH_DIR = ROOT / "data" / "audio_synth"
EN_VOICE, HI_VOICE = "Rishi", "Lekha"

# 300-3400 Hz telephone band, 8 kHz, with light pink noise.
PHONE_FILTER = "[0:a]highpass=f=300,lowpass=f=3400[v];[v][1:a]amix=inputs=2:duration=first:normalize=0"

HINDI_TEXT = {
    "c07": "अखिलेश को ढाई लाख रुपये भेज दो कल सुबह तक",
    "c08": "अनिल कुसुमा से बोलो कि मैं दस मिनट में हाईटेक सिटी पहुँच रहा हूँ",
    "c09": "मेरा यूपीआई आईडी है देवांशी डॉट ढींगरा ऐट द रेट ओके एचडीएफसी बैंक",
    "c10": "नम्या नरेश का ऑर्डर अमीरपेट वाले रत्नदीप के पास डिलीवर करना है",
    "c11": "डॉक्टर मेहता के क्लिनिक में कल सुबह दस बजे का अपॉइंटमेंट कन्फर्म कर दो",
    "c12": "सुशांत कुमार ने स्विगी से बिरयानी ऑर्डर की थी पैराडाइज़ से",
    "c16": "स्वाति मैर को बोलो कि साई गणेश ने पाँच हज़ार रुपये पेटीएम कर दिये हैं",
    "c18": "मुझे सिकंदराबाद से विशाखापट्टनम की ट्रेन टिकट चाहिए पंद्रह दिसंबर की",
    "c21": "ज़ोमैटो वाले को बोलो गेट नंबर तीन पे आ जाये माधापुर में",
    "c23": "हाँ हाँ ठीक है मैं तिरुवनंतपुरम वाली फ्लाइट बुक कर देता हूँ",
    "c25": "अजय साहनी और अभिषेक सिंह कल चीफ गेस्ट के रूप में आ रहे हैं",
    "c26": "मीटिंग बंजारा हिल्स के चटनीज़ में रखते हैं साढ़े सात बजे",
    "c28": "मेरा अकाउंट नंबर है थ्री वन डबल सेवन ज़ीरो फाइव सिक्स एट टू वन फोर",
    "c30": "डेढ़ किलो टमाटर और पाव किलो अदरक बिगबास्केट से मँगवा लो",
    "c32": "अमित नंदा ने याद दिलाया कि एचडीएफसी का होम लोन ईएमआई तीन तारीख को कटेगा",
    "c34": "चंद्रशेखर आज़ाद विद्यालय के पास वाली गली में मोहम्मद इरफ़ान की दुकान है",
    "c36": "कल तिरुपति दर्शन के लिए तीन सौ रुपये वाला टिकट बुक करना है प्रियंका चतुर्वेदी के नाम से",
    "t02": "अखिला दामराजू को पाँच सौ रुपये भेज दो",
    "t04": "सुनील कुसुमा से बोलो कि मीटिंग कैंसल हो गयी है",
    "t06": "मोहम्मद रिज़वान की दुकान टोलीचौकी में है",
    "t08": "डॉक्टर मेहरा का अपॉइंटमेंट कैंसल कर दो",
    "t09": "स्वाति नायर को कॉल लगाओ और बोलो मैं लेट हो जाऊँगा",
    "t11": "लक्ष्मी नारायण राव को बोलो कि रेंट फ्राइडे तक दे दूँगा",
    "n01": "कल सुबह जल्दी उठना है और जिम जाना है",
    "n03": "बिजली का बिल इस हफ्ते भरना है",
    "n05": "मुझे थोड़ा टाइम चाहिए मैं बाद में कॉल करता हूँ",
}


def synthesize(text: str, voice: str, out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.aiff"
        subprocess.run(["say", "-v", voice, "-o", str(raw), text], check=True)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
             "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.015",
             "-filter_complex", PHONE_FILTER, "-ac", "1", "-ar", "8000", str(out)],
            check=True,
        )


def main() -> None:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    made = 0
    for clip in load_manifest():
        out = SYNTH_DIR / f"{clip.id}.wav"
        if out.exists():
            continue
        if clip.id in HINDI_TEXT:
            synthesize(HINDI_TEXT[clip.id], HI_VOICE, out)
        else:
            synthesize(clip.ref, EN_VOICE, out)
        made += 1
    print(f"synthesized {made} clips into {SYNTH_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
