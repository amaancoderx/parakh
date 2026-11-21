# Audio-grounded verification ("re-listening") of ASR output and black-box error localisation from multiple ASR outputs

Scope: evidence for and against (1) sending a disputed audio span plus candidate names to an audio-capable LLM as multiple choice with a "none of these" option, and (2) "cross-examination", which re-transcribes the span once with the true-candidate hint and once with a sound-alike decoy hint. Also covers the best black-box way to localise errors and the practical work of cutting spans. Today is 2026-11-21. "Preprint" means an arXiv paper with no peer-reviewed venue found.

---

## Q1. Audio-grounded re-listening / candidate verification with speech LLMs: gains, zero-shot or not, failure modes

### Takeaway
The closest published designs, ClozeGER and Multi-ASR fusion with a SpeechLLM, show that turning N-best or multi-system disagreements into a constrained choice and adding the audio does help. Both are fine-tuned, though, and ClozeGER's multiple-choice format only works after correcting a strong bias toward option A. Zero-shot evidence for GPT-4o or Gemini as an audio verifier is thin, and what exists is mostly negative: they follow the provided text over the audio 17–23% of the time under conflict, multiple-choice position effects of up to about 24% exist in audio LLMs, and several papers report text dominance and sycophancy. The idea is viable only with mitigations: permuted options, "the candidates may be wrong" framing, a real "none" option, and ideally a blind transcription arm.

### Cited Findings

**"Listen Again and Choose the Right Answer" (ClozeGER): found, peer-reviewed (Findings of ACL 2024)**
- Hu, Chen, Qin, Zhu, Chng, Li. *Listen Again and Choose the Right Answer: A New Paradigm for ASR with LLMs*, Findings of ACL 2024, arXiv 2405.10025. It feeds the source speech (as SpeechGPT discrete units) to a multimodal LLM together with the N-best list, so that corrections stay faithful to the audio, [ACL Anthology](https://aclanthology.org/2024.findings-acl.37); [arXiv](https://arxiv.org/abs/2405.10025v1)
- The format is a cloze test. Tokens shared by all N-best hypotheses become fixed context, and positions where they differ become blanks with options A–E plus a `<NULL>` option. A second post-processing pass fixes errors in the shared context, which the cloze step cannot reach, [arXiv HTML](https://arxiv.org/html/2405.10025v1)
- **Not zero-shot.** It uses LoRA (rank 8, 8.39M trainable parameters) on HyPoradise 5-best output from Whisper-Large across 9 corpora (about 317.7K training pairs), [arXiv HTML](https://arxiv.org/html/2405.10025v1)
- **Position bias is the main failure mode.** On WSJ more than 80% of predictions are option A, because the top-1 hypothesis is usually right and A is usually the training label. Logit calibration fixes this: a prior over option IDs is estimated from cyclic permutations on about 100 validation samples and divided out. Calibration raises WSJ cloze accuracy from 84.7% to 92.6%, [arXiv HTML](https://arxiv.org/html/2405.10025v1)
- Plain ClozeGER without calibration or post-processing underperforms vanilla GER on most sets. Full ClozeGER improves on it, for example CommonVoice 14.4 WER (baseline) to 8.5, against 10.1 for GER with speech; ATIS 7.3 to 2.1; LRS2 12.3 to 7.6, [arXiv HTML](https://arxiv.org/html/2405.10025v1)
- Audio-input ablation (GER without vs with speech): CommonVoice 11.4 to 10.1, LRS2 10.7 to 9.5. On noisy CHiME-4, adding speech made it worse (7.4 to 7.9), [arXiv HTML](https://arxiv.org/html/2405.10025v1)

**LIR-ASR (arXiv 2509.15095, preprint, Sep 2025)**
- *Listening, Imagining & Refining: A Heuristic Optimized ASR Correction Framework with LLMs* (Liu et al.). Despite the name, the "Listening" step means "interpret the initial ASR output". The method appears to be **text-only**: phonetic neighbours come from G2P and character substitution, and an FSM-guided heuristic search runs over up to 8 iterations with a candidate pool of 3, [arXiv HTML](https://arxiv.org/html/2509.15095v2)
- Models are Qwen3-235B and DeepSeek-V3.1, apparently training-free, tested on the FLEURS subset (945 ZH, 647 EN). Whisper-medium ZH CER 5.14 to 3.20 (DeepSeek); EN CER 1.92 to 1.68. The abstract claims "up to 1.5 pp", which is not reconciled with the table. Direct Qwen prompting made Whisper-large-v3 ZH worse (4.22 vs 3.98 baseline). No cost or latency is reported, [arXiv HTML](https://arxiv.org/html/2509.15095v2)

**Better Pseudo-labeling with Multi-ASR Fusion and Error Correction by SpeechLLM (Interspeech 2025, peer-reviewed)**
- Prakash, Kumar, Hacioglu, Sharma, Gopalan, Chetlur, Venkatesan, Stolcke. It replaces voting and arbitration over an ensemble of Icefall, NeMo Parakeet and Whisper-large-v3 with a text LLM or a SpeechLLM, [ISCA Archive](https://www.isca-archive.org/interspeech_2025/prakash25_interspeech.html)
- The SpeechLLM is **Qwen2-Audio** and the text LLM is Llama-3.2-1B-Instruct. **Both are fine-tuned** (QLoRA/LoRA r=32 on about 289 h, ~27K samples of DefinedAI), so neither is zero-shot, [arXiv HTML](https://arxiv.org/html/2506.11089v1)
- Prompt design: uncertain regions are marked inline with system alternatives as a confusion set, e.g. `all|<>|[] right two|<too>|[too] bye` with target "all right you too bye". This is very close to the disputed-span format being considered, [arXiv HTML](https://arxiv.org/html/2506.11089v1)
- WER (ensemble, then text LLM, then SpeechLLM): call-centre set 1 12.92 / 11.39 / 9.85; DefinedAI banking 13.85 / 11.67 / 10.45; GigaSpeech 12.99 / 12.10 / 11.75. On LibriSpeech test-clean the text LLM *hurt* (2.22 to 2.96), while the SpeechLLM roughly matched the ensemble (2.26). Gains are largest in the fine-tuning domain. Hallucination is not discussed, [arXiv HTML](https://arxiv.org/html/2506.11089v1)

**Listening and Seeing Again (AVGER, arXiv 2501.04038, preprint, Jan 2025)**
- Liu, Yuan, Li. N-best output from an AVSR system plus Q-former-compressed audio and visual features form a "cross-modal prompt" to an LLM. It is trained with a multi-level consistency constraint, so it is **not zero-shot**. The paper claims a 24% WER reduction on LRS3 and does not say whether that is relative or absolute, [arXiv](https://arxiv.org/abs/2501.04038)

**Ask, Don't Guess: Targeted Clarification for Speech Recognition Errors (arXiv 2610.24809, preprint, Oct 2026, submitted to NAACL 2027)**
- Parashar, Jyothi, Sarawagi (PARDON). It localises spans likely to improve if re-spoken, then asks the *speaker* to repeat only that span. An LLM rewrites only the flagged span using the transcript of the repetition, [arXiv](https://arxiv.org/abs/2610.24809)
- **Not black-box.** It reads internal RNN-T states (Nemotron Speech Streaming 0.6B, frozen) on AMI, NOTSOFAR-1, CHiME-6 and DiPCo. Spans are capped at 6 words, and the clarification request quotes up to 2 anchor words on each side, [arXiv HTML](https://arxiv.org/html/2610.24809v2)
- The revision LLM (reported as "Gemini 3.8 Flash", temperature 0) removes 23% of word errors on AMI at about 6 interruptions per minute. A zero-interruption N-best correction baseline gets only about 5–6%, against an N-best oracle of about 27–28%, [arXiv HTML](https://arxiv.org/html/2610.24809v2)

**Judge-Editor agent for dysarthric speech (arXiv 2601.21347, ICASSP 2026)**
- Zheng, Dong, Phukon, Hasegawa-Johnson, Yoo. An LLM agent over top-k ASR hypotheses where the judge "keeps high-confidence spans, rewrites uncertain segments". It runs in **zero-shot and fine-tuned modes** and reports a 14.51% WER reduction and +7.66 pp slot micro-F1 on hard samples. It releases the SAP-Hypo5 benchmark and argues that WER is a poor proxy for semantic fidelity, [arXiv](https://arxiv.org/abs/2601.21347)

**Zero-shot GPT-4o / Gemini audio as verifier: direct evidence on text dominance**
- *When Audio-LLMs Don't Listen* (Billa, arXiv 2602.11488, preprint, 2026) uses 57,602 audio–text conflict stimuli in 8 languages. Instructed to follow the audio, **GPT-4o follows the conflicting text 23.2% of the time** (0.9% when the conflict is text vs text). **Gemini 2.0 Flash: 16.6%** (baseline 1.6%), [arXiv](https://arxiv.org/abs/2602.11488)
- In the same study, **framing the transcript as deliberately corrupted reduces text dominance by 80%**, while **forcing explicit transcription increases it by 14%**, [arXiv](https://arxiv.org/abs/2602.11488)
- *When Audio and Text Disagree* (arXiv 2508.15407, preprint, Aug 2025) tested open LALMs (Qwen-Audio-Chat, Qwen2-Audio-Instruct, SALMONN, Audio-Flamingo2 and others, not GPT-4o or Gemini). Text Influence Rate exceeds 95% for most models under adversarial text, and Qwen2-Audio-Instruct audio-QA accuracy falls from 87.5% to 1.5%. Confidence under adversarial text is comparable to or higher than under faithful text, so the model's confidence does not flag the failure. Prompting mitigations give limited gains, and LoRA SFT on 1,000 conflict samples only partly fixes it (1.5% to 42.1%), [arXiv HTML](https://arxiv.org/html/2508.15407v1)
- *DEAF* (arXiv 2603.18048, preprint, 2026) covers 7 audio MLLMs and 2,700+ conflict stimuli. It finds consistent text dominance and separates content-driven bias from prompt-induced sycophancy, [arXiv](https://arxiv.org/abs/2603.18048)
- *SYAUDIO / Hearing is Believing?* (arXiv 2601.23149, preprint) benchmarks audio-LLM sycophancy, including "Are you sure?" pressure, and reports that SFT reduces it. Known only from the search snippet; numbers not retrieved, [arXiv](https://arxiv.org/html/2601.23149)

**Position bias in audio-LLM multiple choice**
- *Hearing the Order* (arXiv 2510.00628, preprint, Hung-yi Lee group, v2 Feb 2026). **Shuffling answer options changes accuracy by up to about 24%** (Phi-4-Multimodal), and by about 5% for Gemini-2.0-Flash and Qwen2.5-Omni. Preferred positions differ by model: Gemini-2.0-Flash generally prefers D, while Qwen2.5-Omni and Phi-4 lean to A. Majority voting over permutations is the recommended mitigation (Phi-4 MMAU 65.27 to 69.24 with full permutation), [arXiv HTML](https://arxiv.org/html/2510.00628v2)
- A KTH study reports that a few rounds of option randomisation may not be enough for speech LLMs, and that position effects interact with speaker gender. Known only from the search snippet, [arXiv](https://arxiv.org/html/2510.02398v1)
- *HalluAudio* (arXiv 2604.19300, ACL 2026) is a benchmark of 5,000+ human-verified QA pairs. It reports deficiencies in acoustic grounding, and the search summary says it found consistent Yes/No biases and non-trivial false refusals. Those numbers are not on the abstract page, [arXiv](https://arxiv.org/abs/2604.19300)

**Other related evidence**
- Zero-shot ChatGPT GER: giving the model the N-best list beats giving only the 1-best, [arXiv 2409.09554](https://arxiv.org/html/2409.09554v1)
- LLMs choosing the better of two ASR hypotheses reach 92–94% agreement with human annotators on HATS, against 63% for WER. The abstract does not say whether audio was given, [arXiv 2604.21928](https://arxiv.org/abs/2604.21928) (preprint)
- PARSA-Bench (Persian) tests GPT-4o-audio and Gemini-2.5-Flash in audio-plus-transcript conditions. Headline numbers not retrieved, [arXiv 2603.14456](https://arxiv.org/pdf/2603.14456)
- OpenAI API: the audio-chat guide names `gpt-audio-1.5` as the audio-capable model in **Chat Completions**, with base64 `input_audio` (WAV in the examples). It says to use Chat Completions, not the Responses API, for audio input, [OpenAI docs](https://developers.openai.com/api/docs/guides/audio-chat-completions)

### Inferences
- **For idea 1:** two peer-reviewed papers (ClozeGER, Prakash et al.) show that restricting the LLM to alternatives at disagreement points, with the audio available, beats free-form correction and text-only correction. Prakash et al.'s confusion-set prompt is almost exactly the "disputed span + candidates" design. PARDON's results also support span-level targeting over whole-utterance rewriting (6-word cap, anchor words).
- **Against idea 1 in the zero-shot setting:** every positive result was fine-tuned. Zero-shot GPT-4o follows conflicting text about 1 time in 4, and multiple-choice position bias is documented. A zero-shot picker will tend to choose the candidate that looks most plausible as text, or the one in its preferred slot, not the one it heard.
- Mitigations the evidence supports:
  - Present the candidates as "guesses that may all be wrong" (corrupted framing cut text dominance by 80%).
  - Run 2–3 cyclic permutations of the option order and take a majority vote (ClozeGER, Hearing the Order).
  - Always include "none of these / unclear".
  - Do **not** ask the model to transcribe first and then choose, since forced transcription raised text dominance by 14%. An exception is a separate blind arm with no candidates shown (next point).
- A cheap sycophancy-free arm: ask the audio LLM to transcribe the short clip **with no candidates**, then match that blind output phonetically against the contact list. Accept only when the blind arm and the multiple-choice arm agree.
- Phone-band Indian speech and Hindi-English names are far from the training domains of every paper above, so expect gains smaller than reported and more "none" answers. Measure on a handful of labelled clips before trusting it.

### Gaps
- No paper found that reports **zero-shot** GPT-4o-audio, gpt-audio or Gemini used specifically as a multiple-choice picker over ASR candidate spans, with WER or entity-accuracy numbers.
- Judge-Editor (2601.21347): which LLM, and whether it hears the audio, were not available from the abstract.
- HalluAudio Yes/No bias numbers, SYAUDIO numbers and PARSA-Bench audio-plus-transcript numbers were not retrieved.
- No study found on Indian-language or Hinglish audio-LLM verification, or on 8 kHz telephone audio in this setting.
- Not confirmed whether `gpt-audio-1.5` supports text-only output (`modalities: ["text"]`), or what its minimum clip length is.

---

## Q2. Prior work resembling the "decoy hint" / counterfactual-prompt test

### Takeaway
**No published work was found that does exactly this test:** re-decoding with the true candidate as hint and again with a sound-alike decoy, and treating "follows whichever hint" as evidence of echoing. The ingredients are well documented, though. Prompted and biased ASR does insert prompted words that were never spoken. Distractor terms are used in training precisely to fight this. One 2025 system jointly decodes context-free and context-conditioned hypotheses to suppress hallucinated bias words. Cross-examination is a novel and well-motivated combination, but it is unvalidated.

### Cited Findings
- **Closest mechanism.** Alibaba Tongyi's hotword-retrieval + RL paper (arXiv 2512.21828, preprint, Dec 2025) *jointly decodes context-free and context-conditioned hypotheses* to keep the RAG benefit "while reducing hallucinations caused by irrelevant biasing words". Its training prompts deliberately include distractor terms, and the GRPO reward credits a bias word being correctly present *or correctly absent*. It reports no separate false-acceptance rate, [arXiv HTML](https://arxiv.org/html/2512.21828v1)
- Same paper: more retrieved candidates means more distractors and worse results. Media-set keyword error rate is 22.63 with no hotwords, 11.99 at top-2 and 15.21 at top-10, so top-2 was chosen. General-domain accuracy dips slightly below the no-hotword baseline, [arXiv HTML](https://arxiv.org/html/2512.21828v1)
- SALMONN-2 (arXiv 2607.17079, preprint) trains contextual biasing with 25–50 random distractors per list. It uses distractor-only lists for utterances that contain no context words and randomly drops true words 10% of the time to reduce over-biasing, [arXiv](https://arxiv.org/pdf/2607.17079)
- Microsoft's LOGIC (arXiv 2601.15397, preprint) reports three things:
  - Speech LLMs "can generate entity phrases that are not even spoken".
  - Prompt-based biasing suffers "list-vomiting", where the model recites the list instead of transcribing.
  - Shallow fusion struggles with distractors that sound like the true phrase.
  LOGIC itself reports about 9% relative entity-WER reduction for a 0.30% increase in false-alarm rate, [arXiv HTML](https://arxiv.org/html/2601.15397v1)
- Whisper prompting: Whisper's prompt was trained to hold the previous segment's text, not a bias list. Prompting with a rare-word list lowered R-WER from 23.7% to 18.0% but raised unbiased-word WER, [arXiv 2502.11572](https://arxiv.org/html/2502.11572v2)
- CB-Whisper (arXiv 2309.09552): long prompts can induce hallucinations, and a comma-separated entity list "may induce hallucination" on harder data, [arXiv HTML](https://arxiv.org/html/2309.09552v3)
- In a non-native-speech study, the prompt "um, uh" triggered a large hallucination that did not appear without the prompt, [arXiv 2503.06924](https://arxiv.org/pdf/2503.06924)
- Consistency check between prompted and unprompted output: a child-speech study flags prompted Whisper output as hallucinated if it is more than 20% longer or 5% shorter than the expected text, and falls back to the unprompted transcript, [arXiv 2506.11079](https://arxiv.org/pdf/2506.11079)
- A 2026 comparison of biasing methods and speech LLMs notes that speech LLMs are sensitive to distractor count, so the authors filtered the biasing list, [arXiv 2608.05759](https://arxiv.org/pdf/2608.05759)
- Audio LLMs follow conflicting text 17–23% of the time even when told to follow the audio (GPT-4o 23.2%, Gemini 2.0 Flash 16.6%). In the same work, a "may be corrupted" framing cut this by 80%, [arXiv 2602.11488](https://arxiv.org/abs/2602.11488)
- OpenAI `gpt-transcribe` has a `keywords` parameter alongside `prompt`, and `gpt-4o-transcribe` / `whisper-1` take `prompt` (whisper-1 limit 224 tokens). So a hinted vs decoy-hinted re-decode can be run on the stock API, [OpenAI STT guide](https://developers.openai.com/api/docs/guides/speech-to-text); [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
- Sarvam: `keyterms` (up to 50 terms of 64 characters each, `saaras:v4` only), with the docs warning that biasing "isn't a guarantee" a term will appear, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)

### Inferences
- Cross-examination is a three-arm extension of the "context-free vs context-conditioned" comparison used in 2512.21828. The arms are no hint, true hint and decoy hint. Read them as follows:
  - True hint yields the candidate, decoy hint yields the decoy, and no hint yields neither: **echoing**, so the span is unresolved.
  - The output stays on the candidate under the decoy hint: **strong evidence it was heard**.
  - No hint already yields the candidate: hearing without help.
- The documented failure modes (inserted bias words, list-vomiting, sensitivity to similar-sounding distractors) are exactly what the decoy arm is designed to expose. That supports the idea's premise, though no paper validates it as a detector.
- **Pick the decoy to be as phonetically close as the true candidate** (for example the next-nearest contact name), and keep hint wording identical across arms. Otherwise the test measures prompt differences, not hearing.
- On genuinely ambiguous phone audio, both arms will often echo. Treat that as "doubtful, escalate to the multiple-choice or blind arm or flag for the user". It is not evidence against the candidate.
- Cost per disputed span is 2–3 extra transcription calls on short clips. The arms can run in parallel.
- A cheaper variant: use the unhinted multi-system outputs as the "no hint" arm, since they already exist, and run only the decoy arm.

### Gaps
- No paper found that uses hint-following under counterfactual or decoy prompts as an uncertainty or hallucination signal for ASR. Searches on "counterfactual prompting", "prompt sensitivity as uncertainty" and "consistency under perturbed context" for ASR turned up nothing direct.
- No measured echo rate for gpt-transcribe / gpt-4o-transcribe `prompt` or `keywords` on names that are absent from the audio.

---

## Q3. Black-box uncertainty and error localisation from multiple decodings or systems; aligning two transcripts (including code-mixed or mixed-script)

### Takeaway
Cross-system disagreement is the standard black-box error signal, from ROVER and complementary-ASR work through to a 2026 eight-system study. It concentrates content errors, but **no source found reports precision, recall or AUC of disagreement against verified ground truth**. The 2026 study explicitly says the accuracy of flagged regions "remains to be established". White-box features (PARDON) beat plain entropy by a wide margin. In the OpenAI stack, the best cheap signal is per-token logprobs from `gpt-4o-transcribe` / `gpt-4o-mini-transcribe`, combined with cross-system disagreement. For code-mixed text, normalise script before aligning: the Hinglish evaluation literature (T-WER) maps English words to one script in both reference and hypothesis.

### Cited Findings
- **Cross-model disagreement (arXiv 2604.14152, Frontiers in AI 2026).** Karbalaie, Seoane, Abtahi. Note: the pith.science URL returned 404, so the arXiv page was used.
  - Setup: 8 ASR systems on 50 medical-education clips (8 h 14 m, 76,398 token positions).
  - Agreement: 72.1% of positions had near-unanimous agreement (7–8 systems) and 2.5% were high-risk (0–3 systems agree). Inter-model ICC was 0.131.
  - The content-error share of disagreements rose from 53.9% to 73.9% across high-risk quintiles. Accent groups differed in high-risk mass (0.7% to 11.4%).
  - **No AUC or precision/recall against human references.** The accuracy of flagged regions "remains to be established", [arXiv](https://arxiv.org/abs/2604.14152)
- Complementary-ASR error detection (Tam et al., ICASSP 2014, SRI) rests on the premise that "a region where two complementary ASR systems disagree is most likely an error". Disagreement is used as a feature in a trained predictor, with reported gains on English and Iraqi Arabic. Numbers not retrieved, [SRI](https://www.sri.com/publication/speech-natural-language-pubs/asr-error-detection-using-recurrent-neural-network-language-model-and-complementary-asr/); [ResearchGate](https://www.researchgate.net/publication/262308966_ASR_error_detection_using_recurrent_neural_network_language_model_and_complementary_ASR)
- e-WER2 aligns word-based and grapheme-based system outputs on the same disagreement premise, [arXiv 2008.03403](https://arxiv.org/pdf/2008.03403)
- **ROVER:**
  - It builds a word confusion network from 1-best outputs and majority-votes per bin, and its result depends on the order in which transcripts are presented.
  - Black-box APIs give only 1-best text, so voting falls back to word frequency. Confidence-weighted voting "significantly" improves results when scores are available.
  - Reference-free quality estimation can choose the ROVER ordering.
 , [Jalalvand et al., arXiv 1706.07238](https://arxiv.org/pdf/1706.07238); [ACL P15-1106](https://aclanthology.org/P15-1106.pdf)
- **How weak plain uncertainty is** (white-box comparison, PARDON, arXiv 2610.24809). On AMI, Tsallis entropy reached AP 38.7 and **4.0% recall at 70% precision**, against 25.3 for the best learned baseline and 32.5 for PARDON. Multi-decode disagreement was *not* tested as a baseline, [arXiv HTML](https://arxiv.org/html/2610.24809v2)
- Whisper hallucination detection: probing decoder states gives F1 62.1%, and LLM-based detectors are less competitive than lightweight text classifiers, [arXiv 2606.23060](https://arxiv.org/html/2606.23060v1). Word-level confidence for Whisper (C-Whisper) requires fine-tuning, [arXiv 2502.13446](https://arxiv.org/html/2502.13446v1). Confidence in noisy speech is overconfident, [arXiv 2509.07195](https://arxiv.org/html/2509.07195v1)
- **Confidence available from the APIs:**
  - `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` and `gpt-4o-mini-transcribe-2025-12-15` support `include[]=logprobs` (only with `response_format=json`). This returns per-token `token`, `bytes` and `logprob`.
  - `gpt-transcribe`, `whisper-1` and `gpt-4o-transcribe-diarize` do not, per the reference page.
 , [OpenAI API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
  - Sarvam documents no word- or transcript-level confidence, only `language_probability`, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)
- **Sampling-based consistency:** no paper found that evaluates sampling multiple Whisper / GPT-transcribe decodings as a word-level error detector. A 2025 quality-estimation paper notes that multi-sample methods cost extra inference runs, [arXiv 2502.11115](https://ar5iv.labs.arxiv.org/html/2502.11115)
- **Code-mixed alignment and scoring:**
  - MUCS 2021 (Hindi-English, Bengali-English) introduced T-WER, which counts an English reference word correct if it appears in Latin script or in its native-script transliteration. The mapping file came from the Google transliteration API, with manual cleaning, [arXiv 2104.00235](https://arxiv.org/pdf/2104.00235)
  - An Interspeech 2021 system replicated T-WER by mapping all English words written in Indic script to Latin forms in *both* reference and hypothesis (T-WER 19.5% Hi-En dev), [ISCA wiesner21](https://www.isca-archive.org/interspeech_2021/wiesner21_interspeech.pdf)
  - PolyWER is a multi-reference metric for code-switched output that mixes transcription and transliteration. Venue unclear: the search summary said Findings 2024, and the likely Anthology entry is linked here but was not opened, [ACL Anthology 2024.findings-emnlp.356](https://aclanthology.org/2024.findings-emnlp.356.pdf)
- Sarvam `saaras` modes include `codemix` (English words in Latin script, Indic words in native script) and `translit` (all Latin). These give a controllable output script for alignment, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)

### Inferences
- The best black-box localiser for this build is a combination, in rough order of cost:
  1. Cross-system disagreement after script normalisation (gpt-transcribe vs gpt-4o-transcribe vs Saaras).
  2. Low per-token logprob from `gpt-4o-transcribe` on the disputed tokens.
  3. Entity-type priors: any token that looks like a name or number is always reviewed.
  Disagreement alone is directionally right but uncalibrated, so tune thresholds on a few dozen labelled clips.
- With only 2–3 systems, ROVER-style voting is weak: with two systems a tie cannot be broken. Disagreement is better used as a *flag* than as a *vote*, which fits the plan of flagging and then verifying.
- Alignment recipe (inferred from T-WER practice):
  1. Romanise or transliterate every hypothesis to one script (or request Saaras `translit`).
  2. Normalise numbers, for example "do sau" / "200" / "दो सौ", to digits.
  3. Run a Levenshtein word alignment with a phonetic or character-similarity substitution cost.
  4. Merge adjacent mismatches into spans, using PARDON's ≤6-word cap with anchor words on both sides.
- Number and name spans deserve special handling: script and format differences ("2 0 0" vs "200") create false disagreements that are not acoustic errors.

### Gaps
- **No source found reporting precision, recall or AUC of cross-system disagreement as a predictor of verified word errors.** That includes 2604.14152, which disclaims it. The Tam et al. 2014 numbers were not retrieved.
- No evaluation found of sampling-based consistency for black-box ASR APIs.
- No published Hinglish-specific multi-hypothesis aligner or tool found. The recipe above is inferred.

---

## Q4. Practical: cutting the disputed span from audio when only text is returned

### Takeaway
Among the OpenAI models, only the deprecated `whisper-1` returns word timestamps, via `verbose_json` with `timestamp_granularities[]=word`. It is still usable until 2027-02-26. Sarvam Saaras returns only chunk-level timestamps. For Hindi/Hinglish, the MMS-based `ctc-forced-aligner` (about 1,130 languages, with romanisation) is the main open option, but its default model is non-commercial and no Hindi accuracy or latency figures were found. For short phone utterances the simplest robust option is often to skip alignment and send the whole utterance (or a padded window) to the verifier with the disputed words marked.

### Cited Findings
- **OpenAI timestamps:** `timestamp_granularities[]` "is only supported for `whisper-1`", with `verbose_json`. `whisper-1` is deprecated and shuts down **February 26, 2027**, and its prompt is limited to 224 tokens, [OpenAI STT guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- The `gpt-4o-transcribe` family supports only `json`/`text` output (no `verbose_json`, so no timestamps), but supports logprobs, [OpenAI API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
- `gpt-transcribe` is the recommended current model, with `prompt`, `keywords`, `languages` and `stream=true`. No timestamp support is stated. `gpt-4o-transcribe` and `gpt-4o-mini-transcribe` are listed as deprecated. Files must be under 25 MB; formats are flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav and webm, [OpenAI STT guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- **Sarvam:** `with_timestamps` returns **chunk-level** (sentence or phrase) timestamps only, not word-level. The REST endpoint is for audio under 30 s, with a Batch API for longer files. `saaras:v3` is legacy and `saaras:v4` is the default, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe). Conflict: a Sarvam marketing page and a SageMaker deployment page advertise word-level timestamps, which the official reference contradicts, [Sarvam try page](https://www.sarvam.ai/try/speech-to-text-api); [SageMaker doc](https://docs.sarvam.ai/api/self-hosted/sagemaker/api-saaras.md)
- **ctc-forced-aligner** (MahmoudAshraf97):
  - Supports Wav2Vec2, HuBERT and MMS models. The default is `mms-300m-1130-forced-aligner`, covering about 1,130 languages with ISO 639-3 codes.
  - `--romanize` is required with the default model for non-Latin scripts.
  - Output can be split by word, sentence or char, and the README claims at least 5x less memory than the TorchAudio forced-alignment API.
  - The code is BSD-2-Clause, but **the default model is CC-BY-NC 4.0**.
  - It takes one `--language` per run, with no documented mixed-language handling and no speed benchmarks.
 , [GitHub](https://www.github.com/MahmoudAshraf97/ctc-forced-aligner)
- The MMS-FA vocabulary is lowercase romanised a–z plus apostrophe, so non-Latin text must be romanised (uroman) first, [HF MMS-FA CoreML card](https://huggingface.co/chordai/mms-fa-aligner-coreml)
- WhisperX's alignment maps language codes to language-specific wav2vec2 models, with a separate Hindi-trained wav2vec2 model for `hi` rather than MMS, [WhisperX alignment.py (HF Space copy)](https://huggingface.co/spaces/Sven33/SATEv1.5/blob/main/transcription/whisperx/alignment.py)
- Alignment accuracy, English only (2024): MFA outperforms MMS and WhisperX at all word-level time tolerances, [arXiv 2406.19363](https://arxiv.org/html/2406.19363v1)
- PARDON quotes up to 2 anchor words on each side of a span of at most 6 words. This is a precedent for padding context around the disputed span, [arXiv HTML 2610.24809](https://arxiv.org/html/2610.24809v2)

### Inferences
- Practical ladder for a 28-hour build:
  1. **No alignment.** If phone utterances are short (a few seconds), send the whole utterance clip plus the transcript with the disputed span bracketed. This avoids alignment cost and errors.
  2. **whisper-1 word timestamps** as a side-channel. Run it in parallel on the same audio, fuzzy-match its words to the disputed span, and cut with ±300–500 ms padding. These padding values are a heuristic, not from a source.
  3. **ctc-forced-aligner** with `--romanize` on a romanised merged transcript, if precise cuts are needed. It is non-commercial by default, which is fine for a hackathon demo.
- Mixed-script text must be romanised to one script before MMS alignment, and the same romanisation helps transcript alignment in Q3.
- Whisper-style timestamps are known to be imprecise, which is the reason WhisperX exists. Generous padding is safer than tight cuts, and very short clips (<1 s) may starve the verifier of context.

### Gaps
- No latency figures found for MMS / ctc-forced-aligner or WhisperX alignment on CPU for short clips. Measure locally.
- No Hindi or Hinglish forced-alignment accuracy benchmark found for MMS, the WhisperX Hindi model, or whisper-1 timestamps.
- Not verified: the accuracy of whisper-1 word timestamps on 8 kHz telephone Hinglish, or whether `gpt-transcribe` will gain timestamps. FuseAlign (arXiv 2609.33650, forced alignment "in the wild") surfaced but was not read, [arXiv](https://arxiv.org/pdf/2609.33650)
