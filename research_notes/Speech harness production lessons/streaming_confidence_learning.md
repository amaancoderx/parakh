# Production patterns for streaming, endpointing, confidence, human correction and learning from corrections (for Parakh, a Hindi/Hinglish API-only ASR harness)

Scope note: researched on 2026-11-21. Vendor claims are labelled "(vendor claim)". Each "Inferences" bullet is my reasoning about what Parakh should do. Those bullets are not sourced facts. Parakh's context: it is API-only over Sarvam Saaras v3/v4 (REST plus streaming) and OpenAI gpt-transcribe / gpt-live-transcribe, it targets Hindi/Hinglish phone calls, it cannot fine-tune, and code freeze is Sun 22 Nov 2026, 2 PM IST.

## 1. Two-pass / streaming-then-correct architectures: how provisional text is shown and patched, and the latency of each stage

### Takeaway
Every major production stack does the same thing. It streams cheap, revisable partials quickly, then replaces them with a "final" for a bounded span once an endpoint is reached. Some stacks (Google two-pass, Azure post-stream refinement, AssemblyAI) also replace that final with a second, more accurate pass that uses more context. The documented budget for the second pass is small: Google's LAS rescoring added less than 200 ms of finalization latency. Parakh's current 3-recogniser ensemble is already a "second pass". What it lacks is a streaming first pass that shows grey provisional text, plus a UI contract that replaces text by segment ID rather than appending it.

### Cited Findings
**Google**
- Google's two-pass E2E ASR streams RNN-T hypotheses, and a LAS decoder rescoring the final output gives a 17–22% relative WER reduction over RNN-T alone. The second pass "increases finalization latency by less than 200ms, which has been considered the limit of acceptable interactive latency". The authors note degradation on long utterances., [Sainath et al., Interspeech 2019 / arXiv 1908.10992](https://arxiv.org/abs/1908.10992)
- The on-device follow-up reports an 8% relative WER improvement "for the same latency" with a model more than 400x smaller. It cuts second-pass time by batching rescoring over lattice arcs., [arXiv 2003.12710](https://arxiv.org/pdf/2003.12710v1.pdf)
- Combining an RNN-T endpointer with LAS and MWER gave an 18.7% relative WER reduction and a 160 ms reduction in 90th-percentile latency., [Li, Chang, Sainath et al., arXiv 2004.11544](https://arxiv.org/pdf/2004.11544.pdf)
- Google Cloud STT streaming: each response contains one `is_final=true` result (the newly settled portion) followed by zero or more `is_final=false` interim results. Interim results carry a `stability` score from 0.0 to 1.0. Google's example shows 0.9 for a portion "unlikely to change" and 0.01 for one "very likely to change". Stability is only populated for interim results, and 0.0 can mean "not computed"., [Google STT v2 StreamingRecognitionResult](https://docs.cloud.google.com/speech-to-text/docs/reference/rest/v2/StreamingRecognitionResult)

**Microsoft Azure**
- Azure Speech emits `recognizing` events (intermediate) and `recognized` events (final)., [Azure: How to recognize speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-recognize-speech)
- Azure "post-stream refinement": monolingual mode "runs a second recognition pass in parallel with real-time streaming". Intermediate results stay low-latency, and "only the final result is replaced with a more accurate version that uses broader audio context", with "no impact to first-token latency".
  - Multilingual mode uses an "LLM Speech streaming model" with open-range language detection and in-session language switching.
  - It is enabled with `SpeechServiceResponse_PostProcessingOption = "PostRefinement"` and requires Speech SDK 1.50 or later for multilingual.
  - Multilingual phrase lists are capped at 200 phrases / 3,200 characters.
  - Source: [Azure: How to recognize speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-recognize-speech); [Azure phrase list](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/improve-accuracy-phrase-list)
- Azure's "Detailed" output returns NBest entries. Each has `Confidence` plus four text forms: Lexical ("actual words recognized"), ITN (numbers etc. normalised), MaskedITN (ITN with profanity masking) and Display (punctuation and capitalisation added). Word-level data comes from the first NBest entry's `Words` array. These details come from Microsoft Q&A answers, not a single reference page., [Microsoft Q&A: output format](https://learn.microsoft.com/en-us/answers/questions/744687/output-format-of-speech-sdk); [Azure display-text format doc](https://learn.microsoft.com/en-us/azure/ai-services/Speech-Service/how-to-custom-speech-display-text-format)
- Display text is a pipeline: audio becomes lexical text, then the default ITN runs, then optional custom ITN., [Azure display-text format doc](https://learn.microsoft.com/en-us/azure/ai-services/Speech-Service/how-to-custom-speech-display-text-format)

**Deepgram**
- Interim results are `is_final:false`. `is_final:true` finalises a segment, and `speech_final:true` marks a detected pause / utterance end. Clients should append every `is_final:true` piece to a buffer and flush the buffer on `speech_final`. Deepgram warns: "Do not use `speech_final: true` alone to capture full transcripts."
- Endpointing defaults to 10 ms. Deepgram recommends 300–500 ms for speakers who pause mid-thought.
- Source: [Deepgram: endpointing & interim results](https://developers.deepgram.com/docs/understand-endpointing-interim-results)

**AssemblyAI**
- Each streaming `Turn` message "re-transcribes the full turn audio and supersedes the previous one". Clients should replace rendered text, not append to it. The final (`end_of_turn:true`) is fully formatted and "the most accurate transcript of the turn"., [AssemblyAI turn detection](https://www.assemblyai.com/docs/universal-streaming/turn-detection)

**OpenAI Realtime transcription**
- Model roles:
  - `gpt-live-transcribe` returns deltas as speech arrives and a final transcript on commit.
  - `gpt-transcribe` starts after a committed turn and also returns `languages` (e.g. `{ "code": "fr" }`, or an empty array if unsure).
- `audio.input.transcription.delay` accepts `minimal | low | medium | high | xhigh`. Lower values give earlier partials, and higher values "give the model more context and can improve word error rate". OpenAI publishes no ms figures and says to benchmark.
- Completion events from different turns "can arrive out of order", so clients must reconcile by `item_id` from `input_audio_buffer.committed`.
- Partial text "may need revision when later deltas correct earlier text".
- `gpt-live-transcribe` returns no word timestamps, speaker labels or confidence scores.
- Session `keywords` (array of literal terms) and `languages` (array, e.g. ISO 639-1) are supported. Keywords cannot contain `<`, `>`, CR or LF.
- Source: [OpenAI Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)
- Pricing: `gpt-live-transcribe` is $0.017/audio-minute and `gpt-transcribe` is $0.0045/min. Both launched around 28–29 July 2026. The live price came from OpenAI model pages via search snippets and aggregators, so verify it on the official pricing page., [OpenAI gpt-transcribe model page](https://developers.openai.com/api/docs/models/gpt-transcribe); [OpenAI gpt-live-transcribe model page](https://developers.openai.com/api/docs/models/gpt-live-transcribe)
- `gpt-transcribe` lists "unstructured context, keyword hints, and multiple language hints" for domain terms and code-switching. Default rate limit at the Build tier is 5,000 RPM., [OpenAI gpt-transcribe model page](https://developers.openai.com/api/docs/models/gpt-transcribe)

**Sarvam realtime STT** (`/speech-to-text-realtime/ws`, default model `saaras:v4`)
- Events are `transcript.partial` and `transcript.final`. Partials are always plain transcription, and `mode` (e.g. `codemix`, `translit`) applies only to the final.
- `stream_type` values:
  - `fast`: "lowest latency", for agents and barge-in.
  - `balanced` (default): "slightly slower, more accurate", for captioning.
  - `simulated`: no partials, only finals.
- `prompt` is "applied to the final transcript".
- `return_timestamps` adds `start_s`/`end_s` to finals only.
- `language_code="auto"` adds `language` to partials and `language_confidence` to finals.
- Source: [Sarvam Realtime STT API](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-api)
- Window sizes: `fast` feeds the model 500 ms audio windows and `balanced` uses 1000 ms windows, so "partials can't arrive sooner than one window". `stream_type` does not delay end-of-speech, because server VAD runs on raw audio.
  - Discrepancy: Sarvam's Pipecat guide lists `fast` as the default, while the API reference and LiveKit guide say `balanced`. Pass it explicitly.
  - Source: [Sarvam LiveKit production best practices](https://docs.sarvam.ai/api/integration/livekit-production-best-practices); [Sarvam Pipecat production guide](https://docs.sarvam.ai/api/integration/pipecat-production-guide)
- Sarvam's older ASR blog claims under 150 ms time-to-first-token in Fast mode (vendor claim; predates the current realtime docs)., [Sarvam ASR blog](https://www.sarvam.ai/blogs/asr)
- Sarvam's suggested latency SLOs for voice pipelines:
  - `transcription_delay` p95: <400 ms good, <700 ms acceptable, >1 s investigate.
  - End-to-end p50: <900 ms good.
  - End-to-end p95: <1.8 s good.
  - Source: [Sarvam LiveKit production best practices](https://docs.sarvam.ai/api/integration/livekit-production-best-practices)

**ElevenLabs**
- Scribe v2 Realtime produces partials in about 150 ms of model latency (vendor claim). It commits segments manually or via VAD silence., [ElevenLabs Scribe v2 Realtime](https://elevenlabs.io/blog/introducing-scribe-v2-realtime); [ElevenLabs commit strategies](https://elevenlabs.io/docs/eleven-api/guides/cookbooks/speech-to-text/realtime/transcripts-and-commit-strategies)

### Inferences
**Adopt the "partial, then final, then refined" contract explicitly.**
- **Tier 0 (provisional, grey, about 0.5–1 s):** stream from Sarvam realtime (`stream_type=fast`, `saaras:v4`, `language_code=hi-IN` or `auto`) or `gpt-live-transcribe` (`delay=low`).
- **Tier 1 (final, black):** at each VAD end, Sarvam `transcript.final` or a commit.
- **Tier 2 (verified, about 1–2 s after the segment ends):** Parakh's existing 3-recogniser ensemble plus the optional hinted pass, run on the committed segment audio. This replaces Tier 1 text in place.
- This mirrors Azure post-stream refinement and Google two-pass.

**Key the UI on segment/item IDs and replace text rather than appending.** This follows the AssemblyAI and OpenAI `item_id` guidance. Show a small "refined" tick when Tier 2 lands. Never patch text that the user has already edited.

**Batch-to-stream adaptation for recorded calls.** Parakh can replay recorded calls through the streaming APIs to demo latency. Because REST is capped at 30 s on Sarvam, the existing 24 s segmentation stays valid for Tier 2.

**The once-per-call 10–35 s LLM discovery step should not block display.** Run it asynchronously and push name corrections as a Tier-3 patch, highlighted as "updated".

**Use `gpt-transcribe`'s `languages` output and Sarvam's `language_confidence`/`language_probability` as cheap code-switch signals for routing.**

### Gaps
- No vendor publishes ms latencies per OpenAI `delay` level, and I found no Hindi benchmark for `gpt-live-transcribe`. Parakh must measure these itself.
- Apple's dictation correction pipeline (beyond the UI) is not publicly documented.
- No official latency numbers for Sarvam `fast` vs `balanced` beyond window sizes and the older <150 ms TTFT blog claim.

## 2. Semantic VAD / endpointing for Indic or code-switched speech

### Takeaway
Silence-only endpointing is the main cause of mid-sentence cuts. Semantic or acoustic turn detectors help, and several now officially cover Hindi:
- LiveKit (text model: Hindi TNR 96.3%, the best of its 14 languages)
- Pipecat Smart Turn v3 (23 languages incl. Hindi, Bengali, Marathi)
- Krisp Turn Prediction v3 (incl. Hindi)
- Deepgram Flux Multilingual (incl. Hindi)

Independent Indic evidence shows stock audio models are mediocre on Indic telephone speech without adaptation: TamilEOT went from 70.3% zero-shot to 83.7–86.1% after training. For a transcription harness (as opposed to an agent), endpointing mainly decides segment boundaries. A cheap, robust recipe is: tuned server VAD, then a turn model or a lexical "trailing connective" hold rule, then a hard max. OpenAI's `semantic_vad` is not available on `gpt-live-transcribe`.

### Cited Findings
**OpenAI**
- `semantic_vad` "uses a semantic classifier to judge, from the words spoken, whether the user has finished". Trailing-off speech gets a longer timeout. `eagerness` is low/medium/high/auto (auto = medium); `low` is suggested for "larger transcript chunks".
- Example `server_vad` config: `threshold` 0.5, `prefix_padding_ms` 300, `silence_duration_ms` 500.
- `gpt-live-transcribe` and `gpt-realtime-whisper` require `turn_detection` to be null and the client to send `input_audio_buffer.commit` (client-side VAD).
- Source: [OpenAI Realtime VAD guide](https://developers.openai.com/api/docs/guides/realtime-vad); [OpenAI Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)
- Semantic VAD max timeouts are 8 s (low), 4 s (medium) and 2 s (high), per the OpenAI Java SDK docs. The main guide does not state them., [openai-java SemanticVad javadoc](https://javadoc.io/static/com.openai/openai-java/4.7.2/com/openai/models/realtime/RealtimeSession.TurnDetection.SemanticVad.html)
- A community post reports that `low` still interrupts during natural pauses (anecdotal)., [OpenAI community thread](https://community.openai.com/t/semantic-vad-request-for-additional-eagerness-settings-below-low/1367398)

**Sarvam**
- Realtime VAD defaults: `threshold` 0.3, `silence_duration_ms` 1000, `prefix_padding_ms` 300, `min_speech_duration_ms` 250. `endpointing="manual"` lets the client send `speech_start` / `speech_end` / `flush`. `config.update` changes thresholds live., [Sarvam Realtime STT API](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-api)
- Sarvam's LiveKit guide gives a server default of 500 ms for `silence_duration_ms`, which conflicts with the 1000 ms above. It recommends these starting points (silence ms / min speech ms / threshold):
  - Telephony: 500 / 200 / 0.7
  - Open-ended conversation: 800 / 120 / 0.6
  - OTP / yes-no: 200 / 60 / 0.5
  - Source: [Sarvam LiveKit production best practices](https://docs.sarvam.ai/api/integration/livekit-production-best-practices)
- The same guide warns that VAD silence and framework `min_delay` stack: "500 ms silence window plus a 0.5 s delay adds a full second of dead air".
  - It suggests temporarily extending `min_delay` (e.g. to 0.8 s) while callers read out digits.
  - It calls LiveKit's turn detector "a weak fit for most Indic languages" and recommends Sarvam VAD plus tuned `min_delay` as "more predictable", while noting the `v1-mini` detector is an option for Hindi.
  - It suggests A/B testing `mode="codemix"` against `transcribe` for Hinglish.
  - Source: [Sarvam LiveKit production best practices](https://docs.sarvam.ai/api/integration/livekit-production-best-practices)
- The legacy Sarvam WS exposes `vad_signals` (START_SPEECH/END_SPEECH events), `high_vad_sensitivity`, `flush_signal` and frame-level VAD knobs (`positive_speech_threshold` 0.7, `negative_speech_threshold` 0.45, `min_speech_frames` 2, etc.)., [Sarvam WS reference](https://docs.sarvam.ai/api-reference/speech-to-text/transcribe/ws)

**LiveKit**
- Multimodal `TurnDetector` (`v1`, `v1-mini` on CPU at about 310–340 MB RAM) covers 14 languages including Hindi.
- The text `MultilingualModel` (Qwen2.5-0.5B, 396 MB, about 50–160 ms per turn) is deprecated. Its Hindi true-positive rate is 99.4% and true-negative rate 96.30%, the best TNR of 14 languages; English TNR is 87.0% (vendor numbers).
- Defaults: `min_delay` 0.5 s and `max_delay` 3.0 s (0.3 s and 2.5 s with the multimodal detector). If no prediction arrives within about 1 s, the turn is committed anyway.
- Source: [LiveKit turn detector docs](https://docs.livekit.io/agents/build/turns/turn-detector/)

**Pipecat Smart Turn v3**
- Audio-only, about 8M parameters, int8 at about 8 MB. Takes up to 8 s of 16 kHz audio, left-padded.
- Latency is "as little as 10ms on some CPUs, under 100ms on most cloud instances", about 65 ms on Pipecat Cloud.
- 23 languages including Hindi. BSD-2 licence.
- Run it only after VAD detects silence. If more speech arrives, re-run on the whole turn.
- Source: [pipecat-ai/smart-turn](https://github.com/pipecat-ai/smart-turn); [Daily: Smart Turn v3](https://www.daily.co/blog/announcing-smart-turn-v3-with-cpu-inference-in-just-12ms/)
- Smart Turn v2 is explicitly trained on per-language filler words and connectives ("and", "but", "so"). ASR models "often ignore critical filler words like 'um' and 'hmm'"., [Daily: Smart Turn v2](https://www.daily.co/blog/smart-turn-v2-faster-inference-and-13-new-languages-for-voice-ai/)

**Hinglish and Indic-specific models and evaluations**
- Community "Smart Turn Hinglish" targets trailing connectives "kyunki…", "lekin…", "matlab…". On a 518-clip Gold Hinglish benchmark, stock Pipecat v3.2 (tau 0.60) scored TNR 67.8%, TPR 72.2%, balanced accuracy 70.0%, ROC-AUC 0.750. The community Whisper-Tiny variant had higher TNR (75.9%) but lower balanced accuracy (60.3%). Community model, not peer-reviewed., [HF: smart-turn-hinglish](https://huggingface.co/abhishek-040010/smart-turn-hinglish)
- Another community Hinglish audio-only detector returns P(turn complete) from the last 8 s and handles Devanagari and romanised fillers and trailing conjunctions (no numbers reviewed)., [HF: hinglish-turn-detector](https://huggingface.co/deveshu/hinglish-turn-detector)
- NAMO turn detector (text-based, mmBERT, ONNX): Hindi accuracy 93.98% (multilingual model), Marathi 88.50%, Bengali 79.40%. Latency under 29 ms (multilingual) or under 19 ms (specialised); about 295 MB. Self-reported in a blog; licence not stated., [NAMO turn detection v1 (dev.to)](https://dev.to/sagarkava/namo-turn-detection-v1-semantic-turn-detection-for-ai-voice-agents-4deg)
- **TamilEOT** (arXiv, Oct 2026; 18,485 labelled boundaries from 116 real Tamil narrowband telephone calls):
  - Smart Turn v3 architecture accuracy rose from 70.30% zero-shot to 83.71% (8.7 MB) and 86.13% (21 MB); ROC-AUC rose from 0.751 to 0.921; under 150 ms single-threaded on a laptop CPU.
  - Replaying boundaries through the production VAD and streaming adapter cost a further 2.60 points, and 7.8% of boundaries "never reach the model at all".
  - Rule-derived negative labels scored 44.4% against a blind human pass. An audio-LLM labeller reached 97.5% agreement for US$5.69.
  - The two false-positive conventions differ about 3x: FP/N 10.1% vs FPR 27.4%.
  - Smart Turn v3's Indic coverage is Bengali, Hindi and Marathi only.
  - Source: [TamilEOT, arXiv 2609.05631](https://arxiv.org/abs/2609.05631)

**Krisp, Deepgram, AssemblyAI**
- Krisp Turn Prediction v3 (May 2026) is multilingual including Hindi, about 9M parameters on CPU, with a single threshold (default 0.5). The share of responses under 200 ms rose from 47% to 69% vs v2 "without more mid-sentence interruptions" (vendor claim; its test set is English-centric, 4 h / 30 speakers). Krisp v2 clean balanced accuracy was 0.82 → 0.823., [Krisp blog: turn-taking v3](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/); [Krisp blog: turn-taking v2](https://krisp.ai/blog/krisp-turn-taking-v2-voice-ai-viva-sdk/)
- Deepgram Flux:
  - `eot_threshold` range 0.5–1.0, default 0.7.
  - `eager_eot_threshold` range 0.3–0.9, off by default; it enables `EagerEndOfTurn` and `TurnResumed` events.
  - `eot_timeout_ms` range 500–60,000, default 5,000.
  - `flux-general-multi` takes a `language_hint`.
  - Source: [Deepgram Flux configuration](https://developers.deepgram.com/docs/flux/configuration)
- Deepgram's language list includes Hindi among the 10 Flux Multi languages., [Deepgram languages](https://deepgram.com/languages); [Deepgram: Flux multilingual](https://deepgram.com/learn/introducing-flux-multilingual)
- Third-party Flux latency figures: median EOT detection under 300 ms and p95 1.5 s, per Together AI (third-party claim); eager mode saves about 150 ms on average, per Telnyx (third-party claim)., [Together AI: Flux](https://www.together.ai/models/flux); [Telnyx release note](https://telnyx.com/release-notes/automatic-eager-end-of-turn-deepgram-flux)
- AssemblyAI does not endpoint on silence alone. At a pause it evaluates the transcript so far, and "entity-aware endpointing" holds the turn open if it ends in something like a phone number.
  - `min_turn_silence` / `max_turn_silence` (ms) by preset: min_latency 128 / 640, balanced 128 / 1280, max_accuracy 512 / 2560.
  - Source: [AssemblyAI turn detection](https://www.assemblyai.com/docs/universal-streaming/turn-detection)

**Azure**
- Azure offers "semantic segmentation" (`Speech_SegmentationStrategy="Semantic"`), which returns finals at sentence-ending punctuation instead of on silence.
  - Limits: continuous recognition only, SDK 1.41 or later, not all locales, no confidence/NBest.
  - Silence segmentation timeout ranges 100–5000 ms (500 typical).
  - Source: [Azure: How to recognize speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-recognize-speech)

### Inferences
**For recorded calls**, segment at VAD pauses as follows:
1. Find pauses of at least 300 ms using Sarvam `vad.speech_end` or Silero.
2. Prefer cut points where the trailing Tier-1 text does **not** end in a Hindi/Hinglish connective or filler ("aur", "lekin", "kyunki", "toh", "ki", "matlab", "yaani", "woh", "jo", "ek minute", "haan toh", "uh/um"). This is a 20-line lexical rule, inspired by AssemblyAI's entity-aware hold and Smart Turn's filler training.
3. Also refuse to cut inside a run of digits or a name.
4. Hard-cap segments at 24–28 s, under Sarvam REST's 30 s limit.

**For live mode:**
- Use Sarvam server VAD at the telephony preset (500 / 200 / 0.7).
- Optionally gate each VAD end through Smart Turn v3 (Hindi in its list, CPU, about 10–65 ms) or the lexical hold rule.
- Raise the hold to about 800 ms when the last partial ends in a connective or is mid-number.
- Use a max of about 2.5–3 s, mirroring LiveKit `max_delay`.
- Because `gpt-live-transcribe` requires client-side commits, Parakh's own VAD/turn logic becomes the shared endpoint authority for all recognisers. This is good for consistent segment IDs across the ensemble.

**Hackathon pitch angle for "semantic VAD":** Parakh can claim "Hinglish-aware endpointing" via (a) the connective/filler hold list and (b) an optional Smart Turn v3 check. Report a small before/after on Parakh's own calls (mid-sentence cut rate), and use the TamilEOT FP/N vs FPR caveat to report the metric honestly.

### Gaps
- No vendor-published Hindi or Hinglish evaluation for OpenAI `semantic_vad`, Deepgram Flux EOT, Krisp v3 or Smart Turn v3 specifically.
- A LinkedIn claim of Hindi false-cutoff rates (11.44% Hindi vs 3.6% English) could not be verified, so it is excluded.
- No source analyses "matlab" or "ek minute" specifically as hold cues. The connective list above is my synthesis.

## 3. Confidence and "abstain/flag" UX

### Takeaway
Word-level confidence from black-box APIs is weak, and the APIs Parakh uses mostly don't expose it:
- `gpt-live-transcribe` returns none.
- Sarvam returns only language probability.
- OpenAI token logprobs exist only on the (deprecated) gpt-4o transcribe family.

HCI evidence says highlighting every low-confidence word does **not** improve correction accuracy, and many users find it irritating. A moderate threshold (about 4% of words highlighted) was rated more useful and made highlighted errors 2.6x more likely to be fixed. The production pattern that works is **tiered grounding**:
- **Accept** when confident, with no mark.
- **Implicit confirm**: show the best guess plus a "did you mean" chip.
- **Explicit ask / abstain**: flag it, don't guess.

Thresholds should be set from error costs. In dialogue data, false acceptances cost more than false rejections. For Parakh, cross-recogniser disagreement on names is a better confidence signal than any single API score.

### Cited Findings
**What confidence the APIs expose**
- OpenAI file transcription: `include: ["logprobs"]` (with `response_format: json`) returns **token** logprobs only for `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` and `gpt-4o-mini-transcribe-2025-12-15`, not for the diarize model. Streaming deltas also carry logprobs.
  - A reference page lists a shutdown date of 2027-02-26 for the gpt-4o transcription models.
  - Word-level aggregation of tokens is left to the developer.
  - Source: [OpenAI Transcriptions API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
- `gpt-live-transcribe` "doesn't return word-level timestamps, speaker labels, or confidence scores"., [OpenAI Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)
- Sarvam Saaras v4 REST documents no confidence fields beyond `language_probability` (0–1, null when the language is fixed). Timestamps are chunk-level, not word-level., [Sarvam Saaras model page](https://docs.sarvam.ai/api/getting-started/models/saaras.md)
- Sarvam WS `data` messages include `language_probability` and `metrics.processing_latency`. `timestamps` is always null over WS., [Sarvam WS reference](https://docs.sarvam.ai/api-reference/speech-to-text/transcribe/ws)

**HCI evidence on confidence highlighting**
- CHI EA '25 evaluated nine commercial ASR services' word confidences for error detection (English data):
  - Precision 0.41–0.55, recall 0.36–0.64, F1 0.33–0.55, AUC 0.68–0.87. The authors call the classifiers "moderate at best".
  - User study (n = 36): balanced threshold (about 4% of words highlighted) vs high threshold (13–21% highlighted) vs none. WER reduction was 0.48 vs 0.45 vs 0.47 (not significant, p = .767).
  - Balanced highlighting was rated more useful than high (4.1 vs 3.3, p = .014). Highlighted errors in the balanced condition had 2.64x higher odds of being fixed.
  - 16 participants preferred no highlighting, 18 balanced and 4 high. 10 of 16 commenters found highlighting irritating, and 7 ignored it over time.
  - Conclusion: "current ASR confidence scores are insufficient for automated error detection".
  - Source: [arXiv 2503.15124 (CHI EA '25)](https://arxiv.org/html/2503.15124v1)
- Vertanen & Kristensson (CHI 2008): underlining low-confidence words "does not overall improve users' ability to detect recognition errors"., [conf_vis_speech_rec.pdf](https://www.keithv.com/pub/confshade/conf_vis_speech_rec.pdf)
- Eyes-free variant: slowing TTS playback on low-confidence words gave 85.3% accurate error detection, better than uniform slowing., [arXiv 2410.20564](https://arxiv.org/html/2410.20564v3)

**Production "did you mean" pattern (Apple)**
- Apple dictation shows a blue underline under words it is unsure of. Tapping offers alternatives; double-tap plus re-dictation replaces the word., [Apple iPhone User Guide: Dictate text](https://support.apple.com/en-asia/guide/iphone/dictate-text-iph2c0651d2/14.0)
- User reports say the tap-for-alternatives behaviour is inconsistent across iOS versions (anecdotal)., [MacRumors forum](https://forums.macrumors.com/threads/ios-dictation-cant-access-blue-underlined-suggestions.2100963)

**Dialogue-systems grounding**
- Bohus & Rudnicky derive state-specific rejection thresholds from data-driven error costs, because "simple thresholds introduce a possibly non-optimal tradeoff between misunderstandings and false rejections"., [MSR: Principled rejection threshold optimization](https://www.microsoft.com/en-us/research/publication/principled-approach-rejection-threshold-optimization-spoken-dialog-systems/)
- Skantze (SIGdial 2007) names explicit verification (CLARIFY) and implicit verification (DISPLAY) as grounding actions between accept and reject. It cites Bohus & Rudnicky (2001) finding that false acceptances were more costly than false rejections., [Skantze 2007](https://preview.aclanthology.org/fix_video/2007.sigdial-1.35.pdf)
- Bohus's thesis treats misunderstandings and non-understandings separately and learns recovery-strategy success rates online., [Bohus PhD thesis, CMU-CS-07-124](https://www.csd.cmu.edu/sites/default/files/phd-thesis/CMU-CS-07-124.pdf)

**Multi-hypothesis evidence for entity correction**
- RECOVER (EMNLP 2026 Industry Track) is a post-ASR entity-correction agent that treats multiple ASR hypotheses as evidence (1-best, entity-aware select, ROVER, LLM-select, adaptive routing). It retrieves candidate entities, has an LLM propose constrained edits, filters them with deterministic guardrails, and has an LLM critic vet each edit.
  - Results: up to 49% relative E-WER reduction and +14 points entity recall vs a Whisper-large-v3 baseline, with overall WER preserved. LLM-Select was the strongest strategy.
  - Source: [RECOVER, arXiv 2603.16411](https://arxiv.org/abs/2603.16411)
- Generative error correction "is unable to reliably introduce words absent from the initial hypotheses, particularly Named Entities". DeRAGEC filters retrieved NE candidates (training-free) and reports a 28% relative WER reduction on CommonVoice/STOP., [DeRAGEC, arXiv 2506.07510](https://arxiv.org/html/2506.07510v1)
- A 2025 three-stage framework adds error pre-detection and reasoning-based verification, because accepting LLM corrections directly "risk[s] hallucination errors"., [arXiv 2505.24347](https://arxiv.org/html/2505.24347v3)

### Inferences
**Build Parakh's confidence from agreement, not API scores.** For each name or entity span, compute:
- (a) how many of the three recognisers agree after transliteration normalisation (Devanagari ↔ Latin, phonetic key);
- (b) whether the span matches a verified user name;
- (c) Sarvam `language_probability` and `gpt-transcribe` `languages`, as code-switch hints.

This is ROVER-style voting, which RECOVER validates for entities.

**Three-tier UX (Ask, don't guess), sized to the CHI EA '25 finding:**
- **Tier A (accept, no mark):** all recognisers agree, or the span matches a verified name.
- **Tier B (implicit confirm):** a majority agrees, or the hinted pass resolved it. Show plain text with a subtle dotted underline and a "did you mean X / Y" chip (Apple blue-underline style). Target about 3–5% of words, not more.
- **Tier C (abstain/flag):** recognisers disagree on a person name and no verified match exists. Render `[name?]` with alternatives and a one-tap "Which name was this?" question. Never silently insert an LLM-proposed name.

**Calibrate tier thresholds from error cost.** A wrong name in a call record is a false acceptance, which is costlier than a flag, so bias toward flagging names but not common words.

**Measure acceptance.** Log tap-through, accept, override and dismiss per chip. CHI EA '25 shows users ignore noisy highlighting, so track the "ignored highlight" rate as a health metric and tighten the threshold if it rises.

**For a phone or IVR flow** (no screen), use the eyes-free equivalent: read back only the uncertain name, slowly ("Did you say Priyanka or Prerna?").

### Gaps
- No published evidence specific to Hindi/Hinglish users' trust in confidence highlighting.
- No calibration study for Sarvam or gpt-transcribe confidence. Neither exposes word confidence.
- I did not verify whether `gpt-transcribe` (the July 2026 model) supports `include: ["logprobs"]`. The reference lists only gpt-4o-family models, so assume no until tested.

## 4. Learning from corrections and personal vocabularies in production

### Takeaway
No vendor lets Parakh fine-tune, but all major APIs accept per-request bias lists. Limits:

| Vendor | Bias mechanism and limit |
|---|---|
| Sarvam v4 | 50 keyterms (≤64 characters each on realtime), updatable mid-call |
| Deepgram | 500 tokens, ideally 20–50 terms |
| AssemblyAI streaming | 100 keyterms |
| ElevenLabs realtime | 50 |
| Azure | ~200 phrases recommended, 2,000 max |
| Speechmatics | ~1,000 recommended |
| Amazon Transcribe | 50 KB tables with DisplayAs |
| OpenAI | `keywords` / `prompt` |

Vendors uniformly warn that over-biasing creates false positives. Academic work shows bias-list noise degrades accuracy beyond about 100 entries. Production systems that learn from users have four traits:
1. They pull context from the immediate situation, e.g. Teams uses meeting invitees.
2. They learn only from explicit correction actions, e.g. Dragon's correction menu, not free edits.
3. They require population or repetition thresholds, e.g. Gboard's k-anonymity k=45.
4. They guard against learning false equivalences: Alexa's feedback loop paper, and LLM memory-poisoning attacks.

### Cited Findings
**Per-vendor limits and guidance**
- **Sarvam:**
  - Saaras v4 supports up to 50 keyterms on REST, Batch and both WebSocket endpoints (v4 only, not v3)., [Sarvam Saaras model page](https://docs.sarvam.ai/api/getting-started/models/saaras.md)
  - The realtime API takes `keyterms` as a JSON array of up to 50 terms of ≤64 characters each, updatable mid-call., [Sarvam Realtime STT API](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-api)
  - Sarvam's LiveKit plugin page says "the realtime plugin has no keyterm list yet", so use a short `prompt`; "a long prompt risks a rejected handshake"., [Sarvam LiveKit production best practices](https://docs.sarvam.ai/api/integration/livekit-production-best-practices)
- **OpenAI:** realtime `keywords` are literal terms, hints "not required output". `prompt` has a length limit, and sessions exceeding it are rejected., [OpenAI Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)
- **Deepgram:** keyterm prompting (Nova-3 mono and multilingual, and Flux) allows 500 tokens per request. "Focus on the most important 20–50 terms". Avoid generic words. Use capitalisation for proper nouns. Published confidence uplifts are "illustrative"., [Deepgram keyterm prompting](https://developers.deepgram.com/docs/keyterm)
- **AssemblyAI streaming:**
  - Maximum 100 keyterms per session, each ≤50 characters. Updatable via `UpdateConfiguration`, and a new array replaces the old one.
  - AssemblyAI "strongly recommend[s] starting with no `keyterms_prompt` and then adding terms as needed". Large lists or common terms "can cause overcorrections and hallucinations".
  - Contextual prompting on 20,000 real voice-agent calls cut WER 21% and named-entity error rate 49% (vendor benchmark).
  - Source: [AssemblyAI keyterms prompting](https://www.assemblyai.com/docs/universal-streaming/keyterms-prompting)
- **ElevenLabs:** keyterms are capped at 1,000 for batch and 50 for realtime (≤20 characters each in one integration guide). A LiveKit doc says keyterms are not supported on `scribe_v2_realtime`, a conflict that is unresolved., [ElevenLabs keyterm prompting](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/keyterm-prompting.md); [LiveKit: ElevenLabs STT](https://docs.livekit.io/agents/models/stt/elevenlabs.md)
- **Azure:**
  - Phrase lists are runtime and need no training. Weight ranges 0.0–2.0 (1.0 default).
  - Use no more than 200 phrases (more increases latency). Multilingual post-stream refinement hard-caps at 200 phrases / 3,200 characters.
  - "A phrase list shouldn't have more than 2,000 phrases". Beyond that, train Custom Speech.
  - Phrase lists are not available for batch transcription.
  - Source: [Azure phrase list](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/improve-accuracy-phrase-list)
- **Google:** phrase-set boost is a float above 0 with a "practical maximum" of 20. "Higher boost values can result in fewer false negatives" but "can also increase the likelihood of false positives". Custom classes allow typed lists., [Google STT model adaptation](https://docs.cloud.google.com/speech-to-text/docs/adaptation-model)
- **Amazon Transcribe:**
  - Custom vocabularies work in all supported languages, within the language's character set.
  - Limits: 100 vocabularies per account, 50 KB per file, ≤256 characters per entry.
  - Table format (Phrase, DisplayAs, plus optional pronunciation columns) is recommended; list format is deprecated.
  - Amazon warns not to put PII in vocabularies.
  - Source: [Amazon Transcribe custom vocabularies](https://docs.aws.amazon.com/transcribe/latest/dg/custom-vocabulary.html)
- **Speechmatics:**
  - `additional_vocab` recommends no more than 1,000 entries per job; the hard cap is 20,000. Entries over 6 words are dropped.
  - `sounds_like` gives alternative pronunciations in the language's main script (e.g. "gnocchi" → "nyohki", "nokey").
  - Realtime caches dictionaries, so the second use is faster; the cache expires after 24 h idle.
  - Source: [Speechmatics custom dictionary](https://docs.speechmatics.com/speech-to-text/features/custom-dictionary)

**Academic evidence on bias-list size**
- Adaptive biasing for transducers degrades once lists exceed about 100 entries, because the entity detector "stays on" and hurts ordinary speech., [arXiv 2306.00804](https://arxiv.org/pdf/2306.00804)
- Large lists add noise that weakens focus on relevant entities, so filtering irrelevant candidates helps., [arXiv 2506.06252](https://arxiv.org/pdf/2506.06252)
- Existing approaches degrade roughly linearly beyond 10k entries., [BR-ASR, arXiv 2505.19179](https://arxiv.org/pdf/2505.19179)
- These figures come from search snippets of the abstracts; I did not read the full texts.

**How production systems learn from users**
- Microsoft Teams live transcription uses "the meeting's invitation, participant names, attachments, etc." to improve accuracy and recognise meeting jargon automatically, "without any human involvement"., [Microsoft Teams blog](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/live-transcription-with-speaker-attribution-now-available-in/ba-p/2228817)
- **Dragon:**
  - Choosing a correction in the Correction menu updates the user's speech profile, and Dragon "uses the corrected words the next time"., [Nuance Dragon: Using Correction](https://nuance.com/products/help/dragon/dragon-for-mac/enx/Content/Correction/CorrectionMenu.html)
  - Correcting a word Dragon actually got right (user said "brunch", Dragon typed "lunch", user "corrects" it to "brunch") "may make your recognition less accurate"., [Nuance Dragon: Correcting recognition errors](https://nuance.com/products/help/dragon/dragon-for-mac/enx/Content/Correction/AboutCorrection.htm)
  - Training guides tell users to fix errors in the Corrections panel rather than by typing directly, because the panel is where learning happens., [Dragon Professional book (Leanpub)](https://leanpub.com/read/dragon-professional-for-windows-book/leanpub-auto-training-phase)
- **Gboard** private OOV-word discovery:
  - Local DP ε = 10; central DP ε = 0.315, δ = 10⁻¹⁰.
  - Each user contributes at most 60 words (about 1 per day over 60 days).
  - Approximate k-anonymity with k = 45, α = 0.95: words from fewer than 45 users survive with probability ≤5%.
  - Discovered words covered 16.8% of OOV words in an en-US test population.
  - Source: [Google, arXiv 2404.11607](https://arxiv.org/html/2404.11607v2)
  - An earlier federated character-LSTM learned OOV words without exporting data., [arXiv 1903.10635](https://arxiv.org/pdf/1903.10635)
- **Alexa** self-learning:
  - It treats user rephrases as implicit error signals and rewrites utterances. Production A/B tests showed a win/loss ratio of 11.8 and over 30% defect reduction., [Feedback-Based Self-Learning, arXiv 1911.02557](https://ar5iv.arxiv.org/html/1911.02557); [Amazon Science blog](https://www.amazon.science/blog/how-we-taught-alexa-to-correct-her-own-defects)
  - A follow-up warns that models retrained on such feedback "can learn false equivalences between original requests and their rewrites"., [NAACL 2022 Industry](https://preview.aclanthology.org/fix_video/2022.naacl-industry.36.pdf)
  - Rephrase detection uses the time gap between turns as a feature., [EMNLP 2021](https://preview.aclanthology.org/moar-dois/2021.emnlp-main.143.pdf)

**Memory-poisoning risk**
- MINJA injects malicious records into LLM-agent memory through ordinary queries alone: 98.2% injection success and 76.8% attack success (authors' figures)., [MINJA, arXiv 2503.03704](https://arxiv.org/abs/2503.03704)
- A later paper reports that moderation tools (Llama Guard) and memory sanitisation were largely ineffective against it, while noting the original setting was idealised., [arXiv 2601.05504](https://arxiv.org/pdf/2601.05504)

### Inferences
**Per-user name memory design** (implementable in hours):
- **Two tiers.**
  - `candidate`: proposed by LLM discovery, or seen once.
  - `verified`: the user explicitly picked it in a "did you mean" chip or the flag-resolution UI, or it independently won ensemble agreement in at least 2 separate calls.
  - Only `verified` names go into keyterm lists and are auto-applied. `candidate` names may only appear as chip alternatives.
- **Learn only from explicit correction actions.** Accepting a chip or resolving a `[name?]` flag counts; free-text edits of the transcript do not (Dragon lesson). Store provenance: call ID, segment, audio offset, the original hypotheses from each recogniser, and the time.
- **Block "correct-to-wrong" learning.** If all three recognisers agreed on X and the user changes it to Y, store Y as a per-call fix but do not promote Y→X as a global mapping without a second confirmation (Dragon's "brunch/lunch" warning; Alexa's false-equivalence warning).
- **Per-call context selection.** Build each call's bias list from:
  - contact or CRM names for the participants (the Teams pattern);
  - the top-N verified names by recency × frequency;
  - LLM discovery output.
  - Cap it to the vendor sweet spot: Sarvam ≤50, Deepgram 20–50, about 100 max anywhere.
  - Never send the whole memory, because bias-list noise beyond about 100 entries hurts accuracy.
- **Decay and eviction.** Use a score like `uses × exp(−age/τ)` with τ ≈ 30–90 days. Evict from the bias list (not from the store) when the score falls below threshold. Store a `last_confirmed_at`, and require re-confirmation if a name is contradicted twice.
- **Spelling variants as `sounds_like`.** Store Devanagari and Latin spellings plus phonetic variants, e.g. "Prerna / प्रेरणा / Prerana", following the Speechmatics `sounds_like` and Amazon `DisplayAs` concepts. Map variants to one canonical display form in post-processing rather than biasing on all of them.
- **Memory-safety rule.** Transcript content and LLM output can never write to `verified` memory, only a user UI action can. This blocks MINJA-style poisoning, e.g. a caller saying "my name is spelled …". Keep memory per user and per tenant, with no cross-user sharing unless k-anonymity-style thresholds are met (Gboard pattern). Don't put PII-heavy vocabularies into vendor-side stored vocabularies (Amazon's warning); pass them per request instead.
- **Start-empty principle.** Add names to the bias list only after they've been missed (AssemblyAI advice). Run the hinted pass only when the unhinted ensemble disagrees, which Parakh already does on about 1 in 5 segments.

### Gaps
- Apple's on-device personalisation of dictation from contacts and corrections isn't publicly documented in detail.
- The user-facing Gboard "personal dictionary" interaction with ASR is undocumented.
- No vendor reports Hindi-specific keyterm uplift numbers for Sarvam, Deepgram, AssemblyAI or OpenAI.
- Amazon Transcribe's hi-IN real-time vs batch custom-vocabulary specifics were not confirmed beyond "all supported languages".

## 5. Full-duplex / voice-agent harness patterns relevant to Indian languages (only as they inform a transcription-correction harness)

### Takeaway
Indic voice-agent stacks (Sarvam with LiveKit/Pipecat, Deepgram Flux Multi, Krisp) contribute three reusable ideas to a correction harness:
- **Speculative work on provisional text**, discarded if the turn resumes: Flux EagerEndOfTurn / TurnResumed, and OpenAI "speculative lookup from transcript fragments".
- **Explicit per-stage latency SLOs and fallbacks**: Sarvam's p95 transcription_delay under 400 ms, and FallbackAdapter.
- **Operational hygiene** for telephony: 8 kHz handling, reconnects and close codes.

I found little primary documentation from Gnani, Bolna, Vapi or Retell on Indic specifics.

### Cited Findings
- **Deepgram eager EOT:** `EagerEndOfTurn` lets you start LLM work early. `TurnResumed` cancels it if the user keeps talking. Lower eager thresholds fire earlier but cause more false starts. Eager mode "reduces E2E agent latency" at the cost of more LLM calls., [Deepgram eager EOT guide](https://developers.deepgram.com/docs/flux/voice-agent-eager-eot); [Deepgram Flux configuration](https://developers.deepgram.com/docs/flux/configuration)
- **OpenAI voice guide:**
  - Recommends starting a "speculative lookup from transcript fragments" before the delegation event, and to "include unused speculative work in your backend cost measurements".
  - Realtime audio input is billed at 1 token per 100 ms.
  - Source: [OpenAI voice latency & cost guide](https://developers.openai.com/api/docs/guides/voice-latency-cost)
- **Sarvam telephony ops:**
  - Upsampling 8 kHz PSTN to 16 kHz is "usually cheaper than degrading the recognizer's input".
  - Neither STT class retries, and a realtime stream never reconnects after a socket failure. Use about 5 s STT timeouts (not 10 s) and `stt.FallbackAdapter` for provider failover.
  - Close codes: 1003 is auth/quota and not transient; 1013 is transient.
  - The false-interruption target is under 2%.
  - Source: [Sarvam LiveKit production best practices](https://docs.sarvam.ai/api/integration/livekit-production-best-practices)
- **Sarvam model capabilities:**
  - Saaras v4 is "optimized for 8 kHz audio" for telephony, covers 22 Indian languages plus English with auto-detection, and has modes transcribe/translate/verbatim/translit/codemix. Batch diarization handles files up to 2 h., [Sarvam Saaras model page](https://docs.sarvam.ai/api/getting-started/models/saaras.md)
  - Realtime accepts `mulaw` / `alaw` at 8 kHz., [Sarvam Realtime STT API](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-api)
- **Azure** multilingual post-stream refinement explicitly supports in-session language switching with open-range detection. This is a reference design for code-switched calls., [Azure: How to recognize speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-recognize-speech)

### Inferences
- **Reuse "eager" for correction.** When Tier-1 text for a segment contains an unknown capitalised token or a name-like span, speculatively fire the hinted pass and the name lookup immediately, then cancel if the segment changes (TurnResumed analogue). Count wasted calls in cost metrics.
- **Instrument Sarvam's SLO table in Parakh's UI or health page:** transcription_delay p95, Tier-2 refine delay p95, flag rate, and chip acceptance. It is cheap to show, and it signals production-readiness to judges.
- **Telephony audio:** feed Saaras v4 at 8 kHz natively (it is optimised for that), or A/B against 16 kHz upsampling (Sarvam's LiveKit guide). Test both on Parakh's calls, since the two docs differ in emphasis.

### Gaps
- No primary technical documentation was retrieved for Gnani, Bolna, Vapi or Retell Indic configurations; I did not search them in depth given scope.
- No full-duplex (speech-to-speech) model evidence specific to Hindi transcription correction was found.

## 6. Cost and latency control patterns

### Takeaway
The highest-leverage controls, all implementable today:
1. **Cascade.** Run the cheap path always and escalate only on disagreement or flags. Parakh's "1 in 5" hinted pass already does this.
2. **Hedged or speculative parallel calls with a p95 trigger and cancellation.** Google's Tail at Scale: a hedge after 10 ms cut p99.9 from about 1,800 ms to 74 ms for +2% requests, per secondary summaries.
3. **Content-hash caching** of (audio hash, model, params, bias-list hash).
4. **Price awareness:**
   - `gpt-transcribe` $0.0045/min
   - `gpt-live-transcribe` $0.017/min (about 3.8x)
   - Sarvam STT ₹30/hour, billed per second
   - Running three recognisers on every segment roughly triples base ASR cost.

### Cited Findings
**Prices**
- `gpt-transcribe` costs $0.0045/min., [OpenAI gpt-transcribe model page](https://developers.openai.com/api/docs/models/gpt-transcribe)
- `gpt-live-transcribe` costs $0.017/min, via OpenAI model page snippets and aggregators; verify before relying on it., [OpenAI gpt-live-transcribe model page](https://developers.openai.com/api/docs/models/gpt-live-transcribe)
- Sarvam STT costs ₹30 per hour of audio (₹45 with diarization), billed per second., [Sarvam API pricing](https://sarvam.ai/api-pricing); [Sarvam pricing docs](https://docs.sarvam.ai/api/getting-started/pricing)

**OpenAI realtime cost mechanics**
- Audio input is 1 token per 100 ms. Keep history static to preserve the cache rate. VAD "will effectively filter out empty input audio". Include unused speculative work in cost., [OpenAI voice latency & cost guide](https://developers.openai.com/api/docs/guides/voice-latency-cost)

**Hedged and tied requests**
- Dean & Barroso, "The Tail at Scale" (CACM 2013): defer the hedge until the first request has been outstanding longer than its class's p95 latency. In a BigTable benchmark, a hedge after 10 ms cut p99.9 latency from 1,800 ms to 74 ms with 2% more requests. Tied requests are also described. The numbers come from secondary summaries of the paper., [Tail at Scale PDF](https://pdos.csail.mit.edu/6.824/papers/tail-dean.pdf); [the morning paper summary](https://blog.acolyer.org/2015/01/15/the-tail-at-scale/)

**Cascade and two-pass precedents**
- Google two-pass keeps the second pass under 200 ms of added finalization latency. Batching lattice-arc rescoring cut second-pass time., [arXiv 1908.10992](https://arxiv.org/abs/1908.10992); [arXiv 2003.12710](https://arxiv.org/pdf/2003.12710v1.pdf)
- Azure monolingual refinement runs the second pass in parallel, with no first-token latency impact., [Azure: How to recognize speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-recognize-speech)

**Caching and limits**
- Speechmatics caches identical custom dictionaries in realtime, so they are faster from the second use; the cache expires after 24 h idle. This is a vendor-side example of hashing config to save init time., [Speechmatics custom dictionary](https://docs.speechmatics.com/speech-to-text/features/custom-dictionary)
- Azure warns that phrase lists over about 200 entries increase latency., [Azure phrase list](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/improve-accuracy-phrase-list)
- Sarvam bills on the server-authoritative `audio_duration_s` in `session.end`., [Sarvam Realtime STT API](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-api)

### Inferences
**Cascade policy for Parakh:**
1. Always run Sarvam v4 plus `gpt-transcribe`, the two cheapest. Sarvam's ₹30/h is about ₹0.5/min, roughly $0.006/min at about ₹85–88/USD (my conversion).
2. Run the third recogniser only when those two disagree on a name-like span or a language switch, or when Sarvam's `language_probability` is low.
3. Run the hinted pass only when the vote is still split.

This turns "3 always plus 1 in 5" into "2 always plus ~k%". Report the measured escalation rate and the cost per call-minute.

**Hedging and timeouts:**
- Set per-recogniser p95 timers from Parakh's logs. If a recogniser exceeds its p95 (e.g. about 1.2 s), fire a duplicate or alternative call and take whichever returns first. Cancel the loser by aborting the HTTP request; note the vendor may still bill.
- Enforce hard timeouts of about 5 s (Sarvam's advice) and fall back to the 2-of-3 result rather than blocking.

**Caching:**
- Key segment results by `sha256(pcm_bytes) + model + mode + language + sorted(keyterms) + prompt_hash`.
- This de-duplicates re-runs during demos and re-processing. It also makes the hinted pass idempotent, and lets LLM discovery results be reused per call hash.
- Cache the LLM discovery output per call as well. It's the 10–35 s long pole, so precompute it asynchronously and never block Tier-1/Tier-2 display on it.

**Latency budget to present** (targets, not measurements):
- Tier-0 partials: ≤1 s (Sarvam `fast` uses 500 ms windows).
- Tier-1 final: ≤0.7 s after end of speech (Sarvam p95 "acceptable").
- Tier-2 refine: ≤2 s after segment end (today about 1 s, plus about 1 s for hinted segments).
- Discovery: async, ≤35 s per call.

### Gaps
- I did not obtain the official OpenAI pricing page render, so the `gpt-live-transcribe` price is via model-page snippets and aggregators.
- No published numbers on audio-hash caching hit rates for ASR APIs.
- No vendor documents whether aborted HTTP transcription requests are billed. Verify with the providers.
- The Tail at Scale figures came from secondary summaries; I did not read the original PDF text.
