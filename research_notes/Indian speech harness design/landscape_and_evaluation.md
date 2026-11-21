# Landscape and evaluation resources for context-aware ASR on Indian (phone) speech

Research date: 2026-11-21. "Vendor-reported" = numbers published by the company selling the model. "Independent" = third-party benchmark (note: Voice of India is run by Josh Talks with AI4Bharat/IIT Madras; it is independent of the ASR vendors but not peer-replicated). Items marked "(search-snippet level)" were seen only in search-result summaries, not on a fetched primary page.

## 1. Open-source projects and research that wrap ASR with LLM correction, contextual biasing, multi-ASR fusion or entity correction for Indian languages / Hinglish

### Takeaway
No public project combines what the hackathon harness proposes: commercial-API ASR, personal context such as contacts, Indian phone audio, Hinglish, and fusion of two ASRs. The nearest work is AI4Bharat's IndicContextEval, which prompts audio LLMs with entity lists. It uses read and extempore speech, not phone audio, and its strongest system improves only modestly with context. Beyond that there is a one-person weekend study of LLM post-correction on top of Saaras v3, Pulse, Prisma and IndicConformer (50 clean read clips), and English-only research on multi-hypothesis entity correction (RECOVER). None of these reports beating Saaras v3 on names or numbers in Indian phone calls.

### Cited Findings
**Most relevant benchmark and research code**
- **IndicContextEval (AI4Bharat, Interspeech 2026).** It asks whether audio LLMs actually use contextual prompts. Data: 56 h of natural speech, 555 speakers, 8 Indian languages, 23 professional domains. It uses a 7-level prompt ladder: L0 no context; L1 language only; L2 + domain metadata; L3 + natural-language description; L4 + entity list in English script; L5 + entity list in native script; L6 + entity list from an unrelated domain (adversarial). Metrics are clamped WER and NEER, the "fraction of reference named entities that are missing or incorrect". Licence CC BY 4.0. Evaluation scripts are listed as "coming soon", but per-utterance predictions and `results/paper_results.csv` are released., [GitHub README](https://raw.githubusercontent.com/AI4Bharat/IndicContextEval/main/README.md); [arXiv 2606.19157](https://arxiv.org/abs/2606.19157)
- **IndicContextEval aggregate WER, L1 (language only) → L5 (native-script entity list), all 8 languages:**
  - GPT-4o: 28.61 → 26.04
  - Gemini 3 Flash: 18.90 → 17.46
  - Sarvam Audio: 16.86 → 15.70
  - Gemma 3n: 38.73 → 43.11
  - IndicConformer (L1 only): 18.81 WER, 29.58 NEER
 , [README](https://raw.githubusercontent.com/AI4Bharat/IndicContextEval/main/README.md)
- **IndicContextEval NEER at L1:** IndicConformer 29.58, Sarvam Audio 25.93, Gemini 3 Flash 25.85, GPT-4o Transcribe 35.59, Gemma-3N 35.50. At L5, Gemini 3 Flash NEER falls to 17.39.
- **IndicContextEval, Hindi L5 WER:** GPT-4o Transcribe 17.5, Gemini 3 Flash 14.3, Sarvam Audio 12.4, Gemma-3N 33.2.
- **IndicContextEval, adversarial wrong-domain entities (L6 vs L1):** Gemma-3N WER rises by 9.22 points. GPT-4o, Gemini 3 Flash and Sarvam Audio move by less than 1 point.
- **IndicContextEval conclusions:** Native-script entity lists help most (a script-mismatch cost of up to 11 NEER points versus English-script lists). Natural-language descriptions beat structured metadata. "Sarvam Audio was largely insensitive to context." Entity lists contain 20–30 entities., [arXiv HTML v2](https://arxiv.org/html/2606.19157v2)
- **NeurIPS 2026 WiML poster, "Towards Robust Context Utilisation in Multilingual ASR for Indian Languages."** It proposes context-conditioned and adversarial-robustness training on top of IndicContextEval. "Experiments are in progress", so no results yet., [NeurIPS page](https://neurips.cc/virtual/2026/163791)

**Small study closest to the harness idea**
- **osbornep8/asr_bench_med50 (blog by Osborne Pereira, 1 Jul 2026).**
  - Set-up:
    - 50 read clips in clean conditions (25 Hindi, 25 Kannada), 2 speakers, including 18 "no-term" control clips.
    - Clinical glossary of about 170 terms.
    - Systems: IndicConformer-600M with CTC hotword boost; Sarvam Saaras v3, Smallest Pulse and Gnani Prisma v2.5, each followed by Claude Haiku 4.5 post-correction with a strict "correct only glossary terms" prompt.
    - Metric: fuzzy term recall, counting a match within 25% character edit distance.
  - Results:
    - Saaras v3 raw recall was 92.7%, rising to 95.8% with the LLM corrector.
    - IndicConformer hotword boost reached 97% overall and 98% on Hindi. Pushing the boost weight past 10 degraded results ("Over-boosting produces wrong terms, not just extra ones").
    - Prisma v2.5 had 88% raw recall and appended unspoken tokens on 3 of 50 clips.
    - LLM post-correction "improves both recall and WER simultaneously for most models".
    - False insertions were 0.000, but the author says the controls never stressed this.
  - Limitations: no significance testing; the commercial APIs were tested without their native biasing features., [blog](https://blog.gopenai.com/contextual-biasing-vs-generative-error-correction-for-indic-languages-836e66951f6b), code: https://github.com/osbornep8/asr_bench_med50

**Entity-correction and fusion research (mostly not Indian)**
- **RECOVER (arXiv 2603.16411, March 2026).** An agentic post-ASR entity-correction framework. It uses multiple ASR hypotheses as evidence, retrieves entities, makes constrained LLM edits, applies deterministic guardrails and an LLM critic. It compares 1-Best, Entity-Aware Select, ROVER, LLM-Select and Adaptive Routing.
  - Results: up to 49% relative reduction in entity-phrase WER (E-WER) and up to +14 points entity recall over Whisper-large-v3, with overall WER preserved. LLM-Select was best.
  - Key quote: "If an entity is entirely absent from the ASR output, text-only post-correction has little signal to recover it."
  - Scope: English-focused., [arXiv](https://arxiv.org/abs/2603.16411)
- **Retrieval-augmented entity correction (arXiv 2409.06062).** Retrieval-augmented correction of named-entity ASR errors with an adapted LLM. Acoustic-neighbour embeddings beat semantic embeddings for retrieving the right entity., [arXiv](https://arxiv.org/pdf/2409.06062) (search-snippet level)
- **DeRAGEC (arXiv 2506.07510).** Denoising named-entity candidates for ASR error correction., [arXiv](https://arxiv.org/pdf/2506.07510) (search-snippet level)
- **AgenticASR (InteractiveASR org, MIT licence).** Multi-turn LLM correction of ASR, described for "multilingual, named-entity-intensive, and code-switching conditions". The example data is Chinese, Hindi is not mentioned, and the repo reports no numbers., [GitHub](https://github.com/InteractiveASR/AgenticASR)

**Hindi / Hinglish correction work**
- **Hindi post-ASR correction (EMNLP 2025 / EACL 2026 short).** Fine-tuned ByT5 and mT5 beat LLMs (LLaMA, GPT-4o-mini) at correcting Hindi ASR output. It reports an "inverse scaling trend": LLMs "degrade in low-resource Hindi settings". No licence file., [GitHub cyfer0618/Post-ASR-Correction-in-Hindi](https://github.com/cyfer0618/Post-ASR-Correction-in-Hindi)
- **CLEAR (IIIT-Delhi).** LLM rescoring of n-best hypotheses for Hindi-English code-mixed ASR, to resolve homophones. Reported S-WER 26.9, P-WER 26.46, T-WER 25.04 (search-snippet level). The repo README says "Instructions will be added soon"., [GitHub flamenlp/CLEAR](https://github.com/flamenlp/CLEAR); [IIIT-D repository](https://repository.iiitd.edu.in/jspui/handle/123456789/1928?show=full)
- **DASHA (arXiv 2603.06373).** Speech-LLM ASR with dialogue-level LLM error correction for Hinglish doctor–patient audio (DISPLACE-M). Reports 18.59% tcpWER., [arXiv](https://arxiv.org/pdf/2603.06373) (search-snippet level)

**Other repos**
- **Hobby voice-agent repos.** None does LLM-based entity correction:
  - vaani-voice-agent: Whisper large-v3-turbo; Hindi/Indian-English loan-servicing agent; "entity-safe" design.
  - indic-speech: Whisper + Qwen2.5-3B correction-before-summary on FLEURS clips.
  - indic-voice-agent: faster-whisper.
 , [vaani](https://github.com/Vaibhav7711/vaani-voice-agent); [indic-speech](https://github.com/munnalurigurucharan-droid/indic-speech); [indic-voice-agent](https://github.com/mathuryashash/indic-voice-agent) (search-snippet level)
- **sarvamai/llm_intent_entity.** Open-source LLM-judge scorer for a binary Intent Score and an Entity Preservation Score (0–1; person and place names, organisations, dates, times, numeric quantities). Uses Gemini on Vertex AI., [Sarvam blog](https://www.sarvam.ai/blogs/evaluating-indian-language-asr)

### Inferences
- The specific combination is not covered by any public project or paper found: personal or contact-list context, Indian telephone audio, Hinglish, black-box commercial APIs, and two-ASR fusion. That supports novelty. It also means there is no published external number to compare against; the hackathon must produce its own baseline.
- Three lines of evidence suggest an LLM corrector over a strong baseline gives modest, not dramatic, gains:
  - Saaras v3's 92.7% → 95.8% term recall on clean read speech.
  - IndicContextEval's roughly 1-point aggregate WER gain from L1 to L5 for Sarvam Audio.
  - RECOVER's warning that text-only correction cannot recover entities missing from every hypothesis.
- Using hypotheses from two ASRs (Saaras + gpt-transcribe) plus a contact list as retrieval evidence is the design best supported by RECOVER and the retrieval-augmented entity-correction work.
- The Hindi post-correction paper's "LLMs degrade Hindi" finding means the corrector must be tightly constrained (edit only entity spans) and checked for regressions on non-entity words.

### Gaps
- I could not open the full RECOVER or Hindi post-ASR correction papers to extract per-dataset numbers. CLEAR's repo has no README results.
- I found no GitHub project specifically on "contact name recognition" for Indian voice agents. Searches surfaced only hobby agents.
- I found no public multi-ASR (ROVER/LLM fusion) study on Indian languages.

## 2. Commercial products: context/keyword biasing for Indian languages and any published entity accuracy

### Takeaway
Most major APIs now accept a keyword or context list. Saaras v3, the hackathon baseline, does **not**: keyterms are `saaras:v4`-only. OpenAI gpt-transcribe accepts `prompt`, `keywords` and `languages`. Hindi biasing is documented or claimed by Sarvam v4, Deepgram (Nova-3 `multi`), ElevenLabs Scribe v2, AssemblyAI Universal-3.5 Pro, Google Chirp 3, Azure, Gnani Prisma v3.0, Smallest Pulse and Navana Bodhi. Published entity-accuracy numbers on Indian speech are almost all vendor-reported and none are for telephone names.

### Cited Findings
**Sarvam**
- **Saaras v3 (11 Feb 2026), vendor-reported.** IndicVoices ~19% WER overall (v2.5 ~22%) and 19.31% on the top 10 languages. Supports diarization, numeral/output-format control and 23 languages. No prompt or keyword feature is described, and no telephone, code-mixed or entity numbers are given., [Sarvam blog](https://sarvam.ai/blogs/asr)
- **Sarvam keyterms are `saaras:v4` only.** Using them with v3 returns the error "'keyterms' is only supported by model 'saaras:v4'".
  - Limits: max 50 keyterms, 64 characters each.
  - Endpoints: REST, Batch and both WebSocket endpoints. The realtime WebSocket accepts `config.update` mid-call.
  - Works in all modes (transcribe, codemix, verbatim, translit, translate). Docs recommend `codemix` to keep terms like "PhonePe" in Latin script.
  - The docs say keyterms "do not guarantee that a term will appear" and publish no accuracy numbers., [Sarvam keyterms docs](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/how-to/keyterms)
- **Saaras v4 (25 Sep 2026), vendor-reported.** Audio encoder plus a 3B hybrid state-space decoder. 16.03% WER on IndicContextEval in the L5 keyword-prompting setting, claimed lowest, with no competitor numbers given. LID error 5.22% across 22 languages. No VoI, telephone or code-mixed numbers., [Sarvam Saaras v4 blog](https://www.sarvam.ai/blogs/introducing-saaras-v4)
- **No independent Saaras v4 figures yet.** A third-party write-up (7 Oct 2026) notes v4 had not been independently tested., [Mindcat](https://mindcat.ai/blog/sarvam-saaras-v4-speech-to-text)
- **Sarvam's evaluation blog (2 Apr 2026)** proposes LLM-WER, Intent Score and Entity Preservation Score, but publishes no comparative numbers., [Sarvam](https://www.sarvam.ai/blogs/evaluating-indian-language-asr)

**OpenAI**
- **gpt-transcribe and gpt-live-transcribe** take `prompt` (free-form context), `keywords` (literal terms) and `languages` (list; replaces `language`).
  - Docs: "Keywords are hints, not required output. The transcript should include a keyword only when the audio contains it."
  - Requests are rejected if keywords contain `<`, `>` or line breaks (per a localised guide, search-snippet level).
  - In Realtime sessions it "automatically uses earlier transcribed turns as context".
  - The docs advise tracking the errors that matter "instead of relying only on word error rate"., [OpenAI transcription guide](https://developers.openai.com/api/docs/guides/transcription.md)
- **Launch and pricing (secondary source).** Launched 29 Jul 2026. GPT-Transcribe $0.0045/min; GPT-Live-Transcribe $0.017/min.
  - Vendor-reported: on OpenAI's Context Aware ASR benchmark, GPT-Live-Transcribe semantic accuracy rises from 38.5% to 44.6% with free-form context.
  - The author warns context-conditioned models "will occasionally hallucinate a keyword it never heard".
  - No Hindi numbers., [dev.to (Luke Oakley)](https://dev.to/lukeocodes/gpt-transcribe-makes-context-the-new-asr-feature-1hi1)

**Deepgram**
- **Keyterm Prompting** works on Nova-3 (monolingual and multilingual) and Flux. Up to 100 terms; hard limit 500 tokens. Docs advise "the most important 20-50 terms". No accuracy figures., [Deepgram docs](https://developers.deepgram.com/docs/keyterm)
- **Multilingual expansion.** Keyterms were extended to Nova-3 multilingual on 26 Nov 2025. Hindi is among the languages Nova-3 `multi` handles for code-switching., [Deepgram changelog](https://developers.deepgram.com/changelog/2025/11/26) (search-snippet level)
- **Hinglish blog (28 May 2026), vendor.** Recommends `language=multi` for Hinglish and up to 100 keyterms. States "Hinglish WER ranges from 26.97% to 69.53% on identical test audio" without naming the models. No Deepgram-specific Hindi or entity numbers., [Deepgram blog](https://deepgram.com/learn/hinglish-voice-ai-speech-recognition)

**ElevenLabs**
- **Scribe v2 keyterm prompting** (batch, medical, realtime; extra cost). Batch: up to 1,000 keyterms of up to 50 characters. Realtime: 50 keyterms of up to 20 characters. English words stay in Latin script in Hindi audio. No Hindi keyterm accuracy published., [ElevenLabs docs](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/keyterm-prompting); [ElevenLabs blog](https://elevenlabs.io/blog/scribe-v2-just-got-an-upgrade) (search-snippet level)

**AssemblyAI**
- **Universal-3.5 Pro (async)** covers 18 languages including Hindi and falls back to Universal-2 otherwise. `keyterms_prompt` accepts up to 1,000 terms of up to 6 words each. On async U-3.5 Pro, `prompt` and `keyterms_prompt` are mutually exclusive., [AssemblyAI docs](https://assemblyai.com/docs/pre-recorded-audio/universal-3-5-pro) (search-snippet level)
- **"When keyterm prompting backfires" (19 Nov 2026).** Adding the variant "Kelly Byrne-Donoghue" made the model mis-transcribe a correctly spoken "Kelly Byrne Donahue" in 3/3 runs; the baseline was correct every time.
  - Gains "did not clearly carry over" to some non-English languages.
  - A scoped list of about 20 terms typically beats an exhaustive list of about 800.
  - Advice: A/B on identical audio, measuring overall accuracy rather than keyterm hit rate, because "Hit rate always improves, so it hides regressions". Treat list changes as deployments., [AssemblyAI blog](https://www.assemblyai.com/blog/when-keyterm-prompting-backfires)

**Google and Microsoft**
- **Google Chirp 3** lists hi-IN as GA, and speech adaptation (phrase biasing) as GA on the English page. The Indonesian-language page lists adaptation as unsupported, so the docs conflict., [Google Chirp 3 docs](https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3) (search-snippet level)
- **Azure**
  - The language-support table lists "Phrase list" for hi-IN, and the fast transcription API supports hi-IN., [Microsoft Learn](https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=stt) (search-snippet level)
  - Azure LLM Speech (Oct 2026) supports up to 2,000 phrases via `phraseList`, but hi-IN support for that model is unconfirmed., [Microsoft Foundry blog](https://devblogs.microsoft.com/foundry/?p=3076) (search-snippet level)

**Gnani**
- **Prisma v3.0 (29 Oct 2026), vendor-reported.**
  - 9 Indian languages + English, with code-switching. Modes: Verbatim, Transcribe, Code-mix, Transliterate.
  - Up to 200 custom-vocabulary terms per request. Supplied-term recall rose from 70.9% to 90.3% "without fine-tuning", which Gnani calls an upper bound measured on public read speech.
  - Vistaar macro WER 16.93 vs ElevenLabs Scribe v2 19.98, Azure 20.51, Deepgram Nova 3 26.57.
  - Hallucinated text on noise-only audio fell from 13.4% to 4.2% versus v2.5. Accepts 8 kHz telephony audio., [Analytics India Magazine](https://analyticsindiamag.com/ai-news/gnani-ai-launches-prisma-v30-speech-recognition-model-for-10-languages)
- **Gnani "speaker names" and find-and-replace.** Reported as passing customer and agent names per call, plus find-and-replace rules for names. Seen only in a LinkedIn post and secondary summaries; no accuracy figure; not in the AIM article., [search result: LinkedIn](https://in.linkedin.com/in/lavelesh) (unverified)

**Smaller vendors**
- **Smallest.ai Pulse** takes `keywords` with optional intensifiers (up to 10,000 per session). The changelog says the default intensifier is 1, the recommended range 1–3, and values above 10 increase "the chance of hallucinating the keyword when it was not spoken". Now also works on pre-recorded HTTP., [Smallest docs](https://docs.smallest.ai/models/documentation/speech-to-text-pulse/features/keyword-boosting); [changelog](https://docs.smallest.ai/models/changelog/pulse-stt) (search-snippet level)
- **Murf** (Finch-1 is on the VoI board): keyword boosting applies only within the keyword's own language., [Murf docs](https://murf.ai/api/docs/speech-to-text/keyword-boosting) (search-snippet level)
- **Navana Bodhi** documents Hindi hotwords (context biasing) and warns against very short particles like "का", "की"., [Bodhi docs](https://navana.gitbook.io/bodhi/quickstart/non-streaming-api/advanced-features) (search-snippet level)
- **Devnagri Black Bird.** A directory listing claims it had the lowest error rate across 15 languages on Voice of India. I found no primary source, and Black Bird does not appear on the current Hindi board., [voiceaispace listing](https://www.voiceaispace.com/tool/devnagri)
- **Bhashini.** No documentation found for hotword or custom-vocabulary support. An integration guide shows plain ASR calls only., [Glific Bhashini guide](https://glific.github.io/docs/docs/Integrations/Bhashini%20ASR)

### Inferences
- **A fair baseline must use native biasing.** gpt-transcribe+keywords is already in the plan. For Sarvam, either justify v3 without keywords (the hackathon's stated baseline, and what Equal AI reportedly uses) or also run Saaras v4+keyterms. Otherwise judges can say "you just didn't use the vendor's keyword feature".
- **Native list limits are a lever for the harness.** Sarvam caps keyterms at 50, Deepgram at about 100 terms or 500 tokens, Realtime ElevenLabs at 50. A full phone contact list (often hundreds of names) does not fit. Retrieval to pick a small, call-specific candidate set, then a correction step, matches AssemblyAI's "scope the list to ~20 terms" advice.
- **Independent false-insertion evidence exists but is thin:**
  - AssemblyAI: near-homophone override.
  - Smallest: high intensifier hallucinates terms.
  - OpenAI: keywords can be hallucinated.
  - Prisma: unspoken token appended on 3 of 50 clips.
  None publishes a false-positive rate on Indian speech, so measuring one is a differentiator.

### Gaps
- No vendor publishes entity- or name-level accuracy on Indian telephone speech. Gnani's 70.9→90.3% is read speech and vendor-reported.
- I did not verify that Google Chirp 3 phrase sets work for hi-IN specifically, or Azure phrase-list quality for Hindi.
- Sarvam's v4 IndicContextEval 16.03% cannot be directly compared with the README table: Sarvam Audio L5 is 15.70 there and v4 is not in the README.
- I did not fetch the Business Today article on Prisma v2.5 claims or the Gnani HF model card.

## 3. Voice of India leaderboard (voiceofindia.ai/stt): Hindi and Hindi-English standings, methodology, openness

### Takeaway
On the live Hindi board (21,020 samples, 33 models, rendered 2026-11-21), Saaras v3 ranks **#2 at 3.69% OI-WER** and OpenAI GPT Transcribe ranks **#16 at 6.94%**. The leader is Bodhan Indic Transcribe Core, labelled open source, at 3.39%. There is **no separate Hindi-English / Hinglish category**; code-mixing is handled inside each language via the lattice. All models run with default settings and **no keyword/biasing lists**. The test set is closed. The OI-WER scorer is public; a public sample set was promised.

### Cited Findings
- **Live Hindi board (OI-WER %, lower is better; "21,020 SAMPLES · 33 MODELS"):**

  | Rank | Model | Vendor | OI-WER |
  |---:|---|---|---:|
  | 1 | Indic Transcribe Core | Bodhan, open source | 3.39 |
  | 2 | Saaras v3 | Sarvam | 3.69 |
  | 3 | Indic Transcribe Flex | Bodhan | 4.01 |
  | 4 | Finch-1 | Murf, streaming, Nov 2026 | 4.69 |
  | 5 | Transcribe | Amazon | 4.69 |
  | 6 | MAI-Transcribe-2 | Microsoft | 4.79 |
  | 7 | MAI-Transcribe-1.5 | Microsoft | 4.91 |
  | 8 | Gemini 3.5 Transcribe | Google | 5.59 |
  | 9 | Scribe v2 | ElevenLabs | 5.76 |
  | 10 | Fast Transcription API | Microsoft | 5.77 |
  | 11 | Maya Transcribe One | Maya Research | 5.85 |
  | 12 | Gemini 3.8 Flash | Google | 6.25 |
  | 13 | Nemotron 3.5 Transcribe | NVIDIA | 6.59 |
  | 14 | Realtime Transcription API | Microsoft | 6.80 |
  | 15 | Gemini 3 Flash | Google | 6.81 |
  | 16 | **GPT Transcribe** | OpenAI | **6.94** |
  | 17 | Prisma v2.5 | Gnani | 7.24 |
  | 18 | SraVaani | ARTPARK & IISc | 7.36 |
  | 19 | Grok Voice Transcribe 2.0 | xAI | 7.84 |
  | 20 | GPT Live Transcribe | OpenAI | 8.42 |
  | 23 | Nova 3 | Deepgram | 8.94 |
  | 25 | GPT Realtime | OpenAI | 10.01 |
  | 26 | Qwen3-ASR | Alibaba | 10.51 |
  | 28 | Ringg | Ringg AI | 11.37 |
  | 30 | GPT-4o mini Transcribe | OpenAI | 17.27 |
  | 31 | Scribe v2 Realtime | ElevenLabs | 26.58 |
  | 32 | GPT-4o Transcribe | OpenAI | 32.27 |
  | 33 | Pingala V1 | Shunya Labs | 35.78 |

  Saaras v4 and Devnagri are not listed. The language selector lists 15 languages, none of them Hinglish or code-mixed., [voiceofindia.ai/stt](https://voiceofindia.ai/stt) (JS-rendered page, read in a browser on 2026-11-21)
- **Earlier snapshots differ** (smaller/different sample):
  - Paper and report Hindi table: Sarvam Audio 5.0, Gemini 3 Pro 6.0, Saarika 2.5 6.2, Amazon 6.8, ElevenLabs Scribe v2 7.7, IndicConformer 8.2, Deepgram Nova 3 13.0, AssemblyAI Universal 19.3, GPT-4o Mini Transcribe 19.6, GPT-4o Transcribe 33.9–34.0. Saaras v3 was not in the paper., [arXiv 2604.19151v4](https://arxiv.org/html/2604.19151v4); [Josh Talks VoI blog](https://voiceofindiablogs.ai.joshtalks.com/)
  - A 25 Jul 2026 snapshot had Bodhan 3.48%, Saaras v3 3.78%, Gemini 3 Pro 4.70%., [Mindcat](https://mindcat.ai/blog/sarvam-saaras-v4-speech-to-text)
- **Methodology.**
  - Data: "unscripted, long-form telephonic conversations"; 536 h, 306,230 utterances, 36,691 speakers, 15 languages, 139 regional clusters.
  - OI-WER = min over valid references of (S+D+I)/N. CER is a diagnostic only. Ranking is per language "with no confidence intervals or tie-banding".
  - Normalisation is version-frozen but the rules are unpublished.
  - Models run through public interfaces with default settings, "No per-model prompt engineering, custom vocabulary or biasing lists"; language is specified only where required.
  - Test set closed "to prevent overfitting"; re-runs happen when major versions ship., [voiceofindia.ai/methodology](https://voiceofindia.ai/methodology)
- **Hindi subset (paper Table 1):** 46.9 h, 22.0K utterances, 4,270 speakers, 306 districts.
  - Recording: contributors recorded dual-channel two-person conversations, "often using low-end smartphones". Sample rate not stated.
  - Lattice construction per the paper: Gemini 3 Flash enumerates variants, then prunes them. A consensus check flags spans where at least 4 of 8 models agree on something missing from the lattice. Spans below 0.5 BERT similarity go to human review., [arXiv HTML](https://arxiv.org/html/2604.19151v4)
  - **Conflict:** the Josh Talks blog says the lattice is "built offline by native-speaking linguists, not by an LLM judge". The blog also states both "1,200+ districts" and "675 districts"., [Josh Talks VoI blog](https://voiceofindiablogs.ai.joshtalks.com/)
- **Openness.**
  - Scorer: the open-source reference implementation is AI4Bharat/OIWER on GitHub, per the blog. A PyPI package `voi-oiwer` describes itself as "the official scorer for OIWER as used in the Voice of India (VoI) ASR benchmark … the same implementation used to produce the benchmark's official results.", [Josh Talks VoI blog](https://voiceofindiablogs.ai.joshtalks.com/); [PyPI voi-oiwer](https://pypi.org/project/voi-oiwer) (search-snippet level; the page did not load)
  - Test data: the paper says an open subset is released via a public submission pipeline, while the blog says a public sample set "will" be released per language. Private-set evaluation is by request (voi-evals@joshtalks.com)., [arXiv](https://arxiv.org/html/2604.19151v4); [Josh Talks blog](https://voiceofindiablogs.ai.joshtalks.com/)
  - The paper's linked repo, github.com/JoshTalks/voice-of-india, returned 404 when fetched.
- **Press coverage (16 Feb 2026)** reported OpenAI models above 55% overall WER and Microsoft missing 6 of 15 languages. These reflect the GPT-4o-era models., [Analytics India Magazine](https://analyticsindiamag.com/ai-news/ai4bharat-josh-talks-benchmark-flags-55-error-rate-for-openai-in-indian-speech)

### Inferences
- **On general Hindi telephone WER, both baselines are already strong, and Saaras v3 nearly halves GPT Transcribe's error rate** (3.69 vs 6.94). Remaining errors are concentrated in rare tokens (names, numbers), which is what the harness targets. Small overall WER changes are expected even when entity accuracy improves substantially; see B-WER in section 5.
- **Default-settings scoring means VoI says nothing about keyword-biased performance.** A harness result is a different axis (context-aware), not a leaderboard competitor. Reporting OI-WER via `voi-oiwer` on the harness's own set would still show "no regression on the overall transcript".
- **The open-source Bodhan models outrank Saaras v3 on Hindi.** Worth knowing if a judge asks whether anyone beats Saaras. This is general WER, not context-aware entity accuracy.

### Gaps
- No Hindi-English-specific VoI numbers exist; the category does not exist on the board.
- I could not confirm whether the public sample set is actually downloadable, or the licence of OIWER/`voi-oiwer`.
- The "Released" column shows Saaras v3 as Jun 2026, versus Sarvam's 11 Feb 2026 blog; it may reflect the evaluated version date.
- The audio sample rate (8 kHz vs wideband) of VoI recordings is not stated anywhere I found.

## 4. Public datasets usable within hours

### Takeaway
For quick Hindi/Hinglish tests the most practical options are:
- **IndicContextEval Hindi** (9.08 h, CC BY 4.0, ships per-utterance entity lists and adversarial lists, the closest to the task).
- **Lahaja** (12.5 h Hindi, entity-heavy per its card, gated with click-through).
- **Svarah** (Indian-accented English with payments/government scenarios, gated).
- **Gramvaani SLR118** (real Hindi phone speech, ~61% 8 kHz; academic-only licence).
- **MUCS 2021 SLR104** (Hindi-English code-switched lectures, 16 kHz, open download).

No public named-entity-labelled Indian *telephone* test set was found. VoI audio is closed.

### Cited Findings
| Dataset | Access | Licence | Size | Conditions / content | Source |
|---|---|---|---|---|---|
| **IndicContextEval** | HF `ai4bharat/IndicContextEval`; gating not stated. A mirror (`Minutor/IndicContextEval`) is gated | CC BY 4.0 | Hindi split: 3,110 utts, 9.08 h, 124 speakers (1,237 read, 1,873 extempore). Total 56 h, 8 languages | Per-row domain metadata and prompts L0–L6 with 20–30-entity lists (L4–L6). Sample rate / device not stated | [HF card](https://huggingface.co/datasets/ai4bharat/IndicContextEval); [README](https://raw.githubusercontent.com/AI4Bharat/IndicContextEval/main/README.md); [HF mirror](https://huggingface.co/datasets/Minutor/IndicContextEval) |
| **Lahaja** | HF gated (agree to share info) | Card body CC BY 4.0, sidebar MIT (inconsistent) | ~12.5 h Hindi, 132 speakers, 83 districts | Read + extempore; card notes content "heavy in named entities and specialized terminology"; `split="test"` | [HF](https://huggingface.co/datasets/ai4bharat/Lahaja) |
| **Svarah** | HF gated | CC BY 4.0 | 9.6 h, 117 speakers, 65 districts | Indian-accented English; read + spontaneous; scenarios include ordering groceries, digital payments, pension claims, passport status | [HF](https://huggingface.co/datasets/ai4bharat/Svarah) |
| **IndicVoices** | HF gated; HF token required | CC BY 4.0 | 23.7K h total (11.2K transcribed), 22 languages, 745 GB; Hindi hours not stated | 8% read, 76% extempore, 15% conversational; `split="valid"` loadable per language and streamable | [HF](https://huggingface.co/datasets/ai4bharat/IndicVoices) |
| **Kathbath** | HF gated | Metadata CC BY 4.0, text says CC0 (inconsistent) | 1,684 h, 12 languages, 174 GB | Read sentences from IndicCorp web text | [HF](https://huggingface.co/datasets/ai4bharat/Kathbath) |
| **Gramvaani Hindi (SLR118)** | Open download (OpenSLR) | "freely for academic purposes"; commercial use needs permission | 100 h train, 5 h dev, 3 h eval labelled; ~1,000 h unlabelled; dev 98 MB, eval 62 MB | Spontaneous **telephone** speech with noise; mp3 at 8–48 kHz (60.87% of train/dev at 8 kHz); crowd-sourced transcripts "vary in accuracy" | [OpenSLR 118](https://openslr.org/118/) |
| **MUCS 2021 Hindi-English (SLR104)** | Open download (OpenSLR) | Not checked | 89.86 h train, 5.18 h test (443 MB test archive) | Code-switched; from spoken tutorials (technical lectures); 16 kHz / 16-bit. Monolingual Hindi is SLR103 | [OpenSLR 104](https://openslr.org/104/) (search-snippet level) |
| **HiACC** | Zenodo record (licence not verified) | Not verified | 5.24 h; 3,318 adult + 1,858 child segments | Hinglish read + spontaneous; token-level language labels; adults in clean conditions, children with noise | [Ulster](https://pure.ulster.ac.uk/en/publications/hiacc-hinglish-adult-amp-children-code-switched-corpus/); [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12329218/) (search-snippet level) |
| **SwitchLingua (audio)** | HF gated plus a signed agreement sent by email | CC BY-NC 4.0, research only, no redistribution | 80+ h, 174 speakers, 11 languages incl. Hindi; per-language hours not given | Code-switching with English; conditions not stated | [HF](https://huggingface.co/datasets/Shelton1013/SwitchLingua_audio) |
| **CS-FLEURS** | Gating not stated | Metadata CC BY-NC 4.0 | XTTS-Test2 42 h across 60 pairs, including Hindi-X | Mostly synthetic (TTS) code-switched audio; a 17 h read test split exists; Hindi-English not confirmed | [HF](https://huggingface.co/datasets/byan/cs-fleurs) |
| **FLEURS** | HF (card did not render) | Not confirmed | 102 languages, ~12 h per language | Read FLoRes-101 (Wikipedia-style) sentences | [arXiv 2205.12446](https://arxiv.org/abs/2205.12446) |
| **Common Voice** | Since Oct 2025 "exclusively available through Mozilla Data Collective"; MDC account and new terms required | MDC terms | Not checked | Read speech | [HF README](https://huggingface.co/spaces/mozilla-foundation/README/blob/main/README.md); [HF CV 17](https://huggingface.co/datasets/mozilla-foundation/common_voice_17_0) |
| **Voice of India** | Closed; private eval on request; public sample set promised | n/a | Hindi 46.9 h / 22.0K utts | Unscripted telephonic conversations | [methodology](https://voiceofindia.ai/methodology) |

- **No Hindi spoken-NER set found.** HiNER is text-only Hindi NER (109,146 sentences). MSNER annotates VoxPopuli (European), and Hindi is not confirmed., [HiNER arXiv 2204.13743](https://www.arxiv.org/pdf/2204.13743); [MSNER](https://arxiv.org/html/2405.11519v1) (search-snippet level)

### Inferences
- **Fastest credible public test set: IndicContextEval Hindi.** It already pairs audio with per-utterance entity lists and adversarial distractor lists, so "context helps / wrong context doesn't hurt" can be shown on a third-party set in hours. It is not telephone and not contact names; downsampling to 8 kHz to simulate phone audio is a possible stress test but would be a researcher-made condition, not a source property.
- **Gramvaani dev/eval (~8 h total, <200 MB) is the only real Indian telephone set found.** It has no entity annotations, and its noisy transcripts make it weak for entity claims unless re-labelled.
- **For contact names plus phone audio specifically, a self-recorded set is unavoidable.** Public sets lack personal-context lists. Record clean and phone-path versions, and use dataset audio only as a secondary "no regression" check.
- **Licence check:** Gramvaani (academic-only) and SwitchLingua/CS-FLEURS (non-commercial) may be fine for a hackathon demo but not a product.

### Gaps
- Sample rates are not stated on the IndicVoices, Lahaja, Svarah, Kathbath or IndicContextEval cards.
- I did not verify FLEURS HF gating/licence (card would not render), MUCS licence, or HiACC licence.
- I did not confirm whether Kathbath HF exposes its "test-known/test-unknown" or noisy splits.
- I did not quantify named-entity or number density in any dataset beyond Lahaja's qualitative note and IndicContextEval's entity lists.

## 5. Credible evaluation practice for an "improves names/numbers with context" claim

### Takeaway
Report:
- **Entity-level metrics:** NEER / entity recall, or B-WER (biased-word WER).
- **Collateral metrics** alongside: U-WER or overall OI-WER/WER, to show no regression elsewhere.
- **An explicit false-insertion test:** no-entity controls plus adversarial or distractor lists, in the style of IndicContextEval L6.
- **Paired bootstrap confidence intervals** over utterances (block bootstrap by call/speaker when utterances are correlated).
- **Baselines with their native keyword features enabled.**
- **A frozen test split** that the prompt/threshold tuning never saw.

### Cited Findings
- **B-WER / U-WER (standard contextual-biasing metrics).** B-WER covers words in the bias list; U-WER covers the others. Insertions count toward B-WER if the inserted word is in the list., [arXiv 2104.02194](https://arxiv.org/pdf/2104.02194.pdf) (search-snippet level)
  - Goal: lower B-WER "without increasing its U-WER significantly". B-WER should stay stable as distractors are added., [arXiv 2401.08835](https://arxiv.org/pdf/2401.08835) (search-snippet level)
  - Full WER moves little because bias words are rare., [arXiv 2604.12398](https://arxiv.org/pdf/2604.12398) (search-snippet level)
- **NEER** = fraction of reference named entities absent or incorrectly transcribed. No matching rule is specified. The L6 adversarial list tests robustness to wrong context., [arXiv 2606.19157v2](https://arxiv.org/html/2606.19157v2)
- **E-WER (entity-phrase WER) + entity recall + overall WER** are reported together in RECOVER., [arXiv 2603.16411](https://arxiv.org/abs/2603.16411)
- **Entity Preservation Score (Sarvam).** An LLM extracts ground-truth entities (names, places, organisations, dates, times, numeric quantities) and checks each against the hypothesis. Utterances without entities score 1.0. Code: sarvamai/llm_intent_entity., [Sarvam blog](https://www.sarvam.ai/blogs/evaluating-indian-language-asr)
- **Fuzzy term recall (≤25% character edit distance)** credits valid transliteration variants without passing wrong words. The study used 18 "no-term" control clips for false insertions, but admits the controls were too easy to stress over-biasing., [Osborne Pereira blog](https://blog.gopenai.com/contextual-biasing-vs-generative-error-correction-for-indic-languages-836e66951f6b)
- **OI-WER** scores against a lattice of valid spellings, so Hindi/Hinglish spelling variants (e.g., English-origin words in Devanagari vs Latin) are not counted as errors. Official scorer: `voi-oiwer` / AI4Bharat OIWER., [voiceofindia.ai methodology](https://voiceofindia.ai/methodology); [Josh Talks blog](https://voiceofindiablogs.ai.joshtalks.com/)
- **A/B practice for biasing lists** (from AssemblyAI's blog):
  - Run identical audio with and without the list.
  - Compare overall accuracy, not hit rate ("Hit rate always improves, so it hides regressions").
  - Scan lists for near-homophones.
  - Measure per language.
  - Re-run when the list changes.
 , [AssemblyAI blog](https://www.assemblyai.com/blog/when-keyterm-prompting-backfires)
- **Vendor guidance on what to measure.**
  - OpenAI: track application-relevant errors "instead of relying only on word error rate"; include target languages, accents and code-switching patterns in test audio., [OpenAI guide](https://developers.openai.com/api/docs/guides/transcription.md)
  - Gnani labels its 70.9→90.3% term recall an "upper bound" because it was measured on read speech with the terms supplied. This shows how in-list recall on easy audio inflates claims., [AIM](https://analyticsindiamag.com/ai-news/gnani-ai-launches-prisma-v30-speech-recognition-model-for-10-languages)
- **Bootstrap significance.**
  - Bisani & Ney (ICASSP 2004): resample utterances with replacement for WER confidence intervals; paired comparisons use the same resamples for both systems. Sentence-level resampling gives narrower intervals than speaker-level., [Bisani bootlog page](https://www-i6.informatik.rwth-aachen.de/~bisani/bootlog.html); [typeset PDF](https://typeset.io/pdf/bootstrap-estimates-for-confidence-intervals-in-asr-4a0uu8tnh9.pdf) (search-snippet level)
  - Applied example: DiarizationLM used 10,000 paired replicates., [arXiv 2401.03506](https://arxiv.org/pdf/2401.03506) (search-snippet level)
  - Correlated utterances (same speaker or call) make plain bootstrap intervals "much narrower than what they should be". Blockwise bootstrap fixes this., [arXiv 1912.09508](https://ar5iv.arxiv.org/html/1912.09508); [arXiv 2209.05281](https://ar5iv.labs.arxiv.org/html/2209.05281) (search-snippet level)
- **Split discipline as practised by VoI:** closed test set "to prevent overfitting", pinned model versions, full request logs, identical normalisation for all systems. It also notes no confidence intervals or tie-banding, which is a known weakness., [voiceofindia.ai methodology](https://voiceofindia.ai/methodology)

### Inferences
Recommended minimal protocol for a 28-hour build, synthesised from the above:
1. **Split.** Split recordings by speaker or call into dev (tune prompts, thresholds, retrieval) and a frozen test set scored once at the end. Publish both counts.
2. **Systems on identical audio:**
   - (a) Saaras v3 raw
   - (b) gpt-transcribe raw
   - (c) gpt-transcribe + keywords (same contact subset)
   - (d) optionally Saaras v4 + keyterms
   - (e) the harness
3. **Primary metric.** Entity accuracy on names and numbers: NEER or entity recall with exact plus fuzzy/OI-style matching. Numbers should match after digit/word normalisation.
4. **Secondary metrics.**
   - B-WER/U-WER or overall WER/OI-WER, to show no collateral damage.
   - **False-insertion rate:** contact names appearing in hypotheses for utterances where they were not spoken. Measure it on no-entity controls and with distractor contacts (near-homophone names) in the list, mirroring IndicContextEval L6 and AssemblyAI's homophone case.
5. **Statistics.** Paired bootstrap (e.g., 10,000 resamples, block by call/speaker) on the per-utterance difference in entity errors. Report the 95% CI and whether it excludes 0. With roughly 30–100 utterances, expect wide intervals; say so.
6. **Third-party check.** Run the same harness on IndicContextEval Hindi, with its entity lists as "context", to show the method generalises beyond self-recorded data.

### Gaps
- I found no published entity-level false-positive rate for any commercial API on Indian speech; the harness would be first to report one.
- I did not find an Indian-language study applying paired bootstrap to entity metrics specifically.
- IndicContextEval's NEER matching rule (exact vs normalised) is unspecified, and its scoring scripts were unreleased as of the README fetch.
