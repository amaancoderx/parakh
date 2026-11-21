# Contextual biasing of speech recognisers: failure modes, training-free mitigations, and the OpenAI and Sarvam APIs (as of 2026-11-21)

Scope: (a) evidence that bias lists and prompts cause false-positive (hallucinated) keywords, how that scales with list size, distractors and list order, and training-free mitigations; (b) the current, official biasing and audio features of OpenAI (gpt-transcribe and related models, plus audio-input chat models) and Sarvam (Saaras v3/v4), and whether Equal AI describes any extra layer on top of Saaras. Research date is 2026-11-21. Where a fact could not be confirmed from official docs, it is marked.

---

## Q1. Does biasing or prompting make the model output listed words that were not spoken, and how does this scale with list size, distractors and list order? What metrics are used?

### Takeaway
Yes. Bigger and noisier bias lists reliably hurt both prompt-based speech LLMs and dedicated biasing modules. The clearest 2026 evidence (Huber & Waibel, arXiv 2608.05759) shows speech-LLM biased-word WER getting 39% to 570% worse (relative) with 250 distractors. Speech LLMs are also sensitive to where a word sits in the prompt (words at the start help more). Dynamic-vocabulary biasing gets up to 55% worse when the correct word is absent from the list, and the authors trace this mostly to insertions of list tokens. OpenAI's own docs warn that keywords can make unspoken terms appear. The standard metrics are B-WER, U-WER and overall WER. Few papers report a dedicated false-alarm rate, so the harness should measure insertions on utterances where no listed name was spoken.

### Cited Findings
**Huber & Waibel 2026, "How to Recognize New Words: A Comparison Between Context Biasing Methods and Speech LLMs" (KIT/CMU, arXiv 2608.05759, submitted 6 Aug 2026)**
- They compare two Whisper large-v2 biasing methods (A: context-attention layers; B: OWSM-style dynamic vocabulary) against three prompted speech LLMs: Qwen3-ASR 1.7B, Qwen3-Omni 30B and VibeVoice-ASR 9B. Test sets are LibriSpeech (read speech) and Earnings-21 and Yodas (non-read speech), [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- Distractor counts tested were 0, 10, 100 and 250, drawn from other rare words in the test set. They also tested a condition where the relevant word is removed from the list. Metrics are BWER (WER on words in the bias list), UWER (WER on all other words) and overall WER. No separate hallucination or false-positive rate is reported, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- Adding 250 distractors makes speech-LLM BWER worse "between 39% and 570% relative". Qwen3-ASR is robust to 10 distractors and sometimes slightly better than with none, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- List order: "the speech LLMs perform better if a word is at the beginning of the prompt". The authors sorted prompt words alphabetically to keep the comparison fair, and they did not quantify the order effect separately. The biasing modules are order-agnostic, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- Method B (dynamic vocabulary) with 250 distractors: BWER rises up to 17% relative when the correct word is in the list and up to 55% when it is absent. The authors attribute most of the added errors to insertions, where the model wrongly emits a dynamic list token. Method A rises less (up to 2% and 17%), [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- With no distractors, biasing cuts BWER by 37–70% relative (Method A) and 48–88% (Method B), with UWER improving by up to about 5–6%, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- Speech LLMs do well on read speech (Qwen3-Omni BWER 1.1% on test-clean with context and no distractors) but generalise worse to non-read speech. On Earnings-21 without context, Qwen3-ASR has 14.51% WER and Qwen3-Omni 22.57%, against 13.52% for Whisper. At 10 distractors on Earnings-21 and Yodas, Method B beats all three speech LLMs, and the gap widens as the list grows, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- Conclusion: use dedicated biasing when a clean list is available and robustness to long or noisy lists matters. Speech LLMs are more flexible but sensitive to prompt composition and word order, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)

**Other evidence on list size, distractors and hallucination**
- BR-ASR (Gong et al., Interspeech 2025, arXiv 2505.19179) states that "excessive prompt length induces LLM hallucinations, leading to unreliable ASR outputs" and that speech-LLM bias lists are typically "limited to dozens of entries". It reports B-WER of 2.8%/7.1% on LibriSpeech test-clean/test-other with 2,000 bias words, and only 0.3% absolute WER and 2.9% absolute B-WER degradation when scaling from 2k to 200k entries via retrieval. Figures come from the abstract and search snippets, not the full paper, [arXiv 2505.19179](https://arxiv.org/pdf/2505.19179); [ISCA archive](https://www.isca-archive.org/interspeech_2025/gong25_interspeech.html)
- CMT-LLM (Interspeech 2025) reports that performance declines once the bias list exceeds 1,000 words, and that raising the list from 100 to 400 words significantly increased both WER and B-WER. It also reports that keeping the filtered list below about 200 words kept coverage with less interference. (Search-snippet level; full paper not read), [arXiv 2506.12059](https://arxiv.org/html/2506.12059v1)
- Hou et al. (Interspeech 2025, "Ranking and Selection of Bias Words") report that Whisper-based B-WER reductions become negligible at 500 or more list words. (Search-snippet level), [ISCA archive](https://www.isca-archive.org/interspeech_2025/hou25_interspeech.pdf)
- Xu et al. (Interspeech 2023, Adaptive Contextual Biasing) note that personalised entity lists lead the model to mistake non-entity words for entities, especially phonemically similar ones, and that performance is sensitive once lists grow past about 100 words. This is directly relevant to sound-alike contact names. (Search-snippet level), [ISCA archive](https://www.isca-archive.org/interspeech_2023/xu23d_interspeech.pdf)
- A zero-shot OWSM prompting study using 100 space-separated biasing words found the base model "cannot distinguish between useful contextual information and distractions". A trie-based biasing study found gains shrink as distractor count N grows, "likely because the method biases to the wrong rare words". (Search-snippet level), [arXiv 2502.11572](https://arxiv.org/pdf/2502.11572); [arXiv 2509.09196](https://arxiv.org/pdf/2509.09196)
- Whisper's prompt was trained to carry the previous segment's transcript, not a word list, so using it for biasing is "misaligned". The paper's fine-tuned fix cut rare-word WER by 45.6% compared with plain prompting, which implies plain Whisper prompting is weak. (Search-snippet level), [arXiv 2306.01942](https://arxiv.org/pdf/2306.01942)
- Apple's phonetic-retrieval LLM study found that adding too many candidates hurt results, attributed to a "noisier contextual prompt". Name error rate was 12.15% with 1 candidate, 10.52% with 5, 10.28% with 10 and 10.57% with 20, [arXiv 2409.15353](https://arxiv.org/html/2409.15353)

**Vendor warnings**
- OpenAI calls keywords "hints, not required output". It advises including only relevant terms and checking "whether they improve accuracy without causing unspoken terms to appear", [OpenAI speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- Sarvam: "Keyterms bias recognition; they do not guarantee that a term will appear in the transcript." Sarvam's docs give no warning about false insertions, [Sarvam keyterms how-to](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/how-to/keyterms)
- A third-party guide (not official) says that too many or irrelevant keywords "may trigger unspoken words to appear", and recommends A/B testing error rates with and without keywords, [Speech Notes blog](https://speechnotes.org/blog/gpt-transcribe-explained)

**Metrics in use**
- B-WER/BWER (error on bias-list words), U-WER/UWER (error on everything else) and overall WER, [arXiv 2608.05759](https://arxiv.org/html/2608.05759); [arXiv 2609.30694](https://arxiv.org/html/2609.30694)
- Named-entity error rate (NER) alongside WER, [arXiv 2409.15353](https://arxiv.org/html/2409.15353)
- Keyword error rate (KER), [arXiv 2512.21828](https://arxiv.org/abs/2512.21828)
- Keyword miss rate, WER and CER (BaLEEN reports an 8.7% relative miss-rate drop, 21% WER gain and 28% CER gain), [arXiv 2609.36913](https://arxiv.org/abs/2609.36913)
- Precision and recall (TP/FP/FN) of the list filter, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)

### Inferences
- With 100+ contacts including sound-alikes, pasting the whole list into `keywords` or `keyterms` is the high-distractor regime that degrades speech LLMs (gpt-transcribe is almost certainly a speech-LLM-style decoder; its architecture is not documented). Expect both substitutions to the wrong sound-alike and insertions of names that were never spoken. The harness should cut the list per utterance to roughly 10 candidates or fewer.
- Order matters for LLM-style recognisers. If several candidates are sent, put the most likely first, or randomise and test both, because a fixed alphabetical order can systematically favour early names.
- B-WER alone hides over-biasing. The harness eval should also report:
  - a name false-positive (insertion) rate on utterances that contain no contact name, or a name not in the list (Huber & Waibel's "relevant context removed" condition);
  - U-WER, to catch damage to numbers and Hinglish words;
  - name-level precision and recall, broken out by "sound-alike distractor present" and "not present".
- "Distractor" in these papers means unrelated rare words. Deliberately confusable sound-alike names, as in this test set, are a harder case than most published setups, so published distractor curves probably understate the problem.

### Gaps
- None of the papers read quantifies a keyword hallucination (false insertion) rate for prompted speech LLMs as a separate metric. Huber & Waibel come closest: they attribute insertions to Method B, and their speech-LLM no-context BWER changes little.
- CLAR (arXiv 2603.25460): only the abstract was available. It claims gains in hotword retrieval, CER and B-WER, with no distractor or false-positive analysis and no numbers in the abstract.
- BaLEEN and the GLCLAP + GRPO paper (2512.21828): only the abstracts were read. No false-positive or list-size scaling data was available, and both require training (a hypernetwork, a retriever, GRPO fine-tuning), so neither applies directly to a black-box API.
- No published study was found that measures distractor sensitivity of OpenAI gpt-transcribe `keywords` or Sarvam `keyterms` specifically, or on Indian or Hinglish phone speech.
- CMT-LLM, Hou et al. and Xu et al. figures are search-snippet level; their full papers were not read.

---

## Q2. Which training-free mitigations work with black-box APIs (retrieval, two-pass biasing, verification, distractor-aware scoring)?

### Takeaway
The best-supported pattern is: first pass with no biasing, then find the likely name spans, retrieve a few phonetically close candidates for those spans only, then run a second, biased pass (or have an LLM correct the text), then optionally verify. Apple reports a 73.6% relative name-error reduction with phonetic retrieval of 10 or fewer candidates. Hitachi's training-free selective retrieval cuts queries by 93% and improves B-WER without hurting U-WER. Huber & Waibel's yes/no audio-LLM filter prevents most of the collapse at 250 distractors. All three need only model inputs and outputs, so they can be adapted to APIs, though none was tested on commercial APIs.

### Cited Findings
**Phonetic retrieval, then LLM generation (Apple, Lei et al., arXiv 2409.15353, Sep 2024)**
- Three steps: the LLM detects named entities without context; detected entities query a personal database for phonetically similar entries; the LLM then decodes again with those candidates, [arXiv 2409.15353](https://arxiv.org/html/2409.15353)
- The contacts test set has 12k contacts across 11.2k queries, with "hundreds of contacts" per user on average and at most 10 candidates in the prompt, [arXiv 2409.15353](https://arxiv.org/html/2409.15353)
- Phonetic match uses normalised phonetic distance (NPD): phoneme edit distance divided by query phoneme count. A candidate is kept if NPD is below 0.2 or no more than 1.2 times the best NPD. The authors note that plain edit distance ignores which phonemes are similar, [arXiv 2409.15353](https://arxiv.org/html/2409.15353)
- Results on contacts:
  - Baseline: WER 6.36, NER 37.52.
  - Full method: WER 4.44, NER 9.90 (30.2% relative WER and 73.6% relative NER reduction).
  - Simple entity replacement without LLM re-generation: WER 4.84, NER 12.60, which is worse.

  [arXiv 2409.15353](https://arxiv.org/html/2409.15353)
- Best at about 10 candidates; 20 candidates was slightly worse (see Q1), [arXiv 2409.15353](https://arxiv.org/html/2409.15353)

**Error-aware selective retrieval with two passes, training-free (Hitachi, Yamashita et al., arXiv 2609.30694, Sep 2026)**
- Pass 1: Qwen3-Omni produces a transcript plus a list of likely domain-term error spans, prompted with four audio-text in-context examples (error-free, substitution, term heard as common words, phonetically similar substitution). Spans are capped at two words, and numeric-only spans are discarded, [arXiv 2609.30694](https://arxiv.org/html/2609.30694)
- Retrieval runs only for predicted spans, using Acoustic Neighbor Embeddings (phonetic, used off the shelf). If no span is predicted, retrieval and pass 2 are skipped. Pass 2 sends the audio, the pass-1 hypothesis and the top-K terms as prompt context, [arXiv 2609.30694](https://arxiv.org/html/2609.30694)
- Results on MedSyn:
  - Queries per utterance drop from 13.37 to 0.99.
  - Top-10 second pass: WER 7.30 → 5.67, B-WER 41.43 → 28.05, U-WER 2.80 → 2.72 (no U-WER damage).
  - Top-10 beat top-50 (B-WER 28.05 vs 29.79).

  [arXiv 2609.30694](https://arxiv.org/html/2609.30694)
- Other domains:
  - ATCOSIM: B-WER 46.40 → 30.65.
  - Earnings: B-WER 50.93 → 45.66, with 1.38 queries per utterance versus 32.71 when querying every word.

  [arXiv 2609.30694](https://arxiv.org/html/2609.30694)
- It does not report false-alarm rates or compare against feeding the whole dictionary. It was tested only on an open-weight model, [arXiv 2609.30694](https://arxiv.org/html/2609.30694)

**Verification filter with an audio LLM (Huber & Waibel, arXiv 2608.05759)**
- Qwen3-Omni is asked once per (audio, list word) pair whether that word is present, and the list is filtered accordingly, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- Filter precision/recall: Earnings-21 34.1%/93.8%, LibriSpeech test-clean 85.1%/98.8%, test-other 59.7%/97.0%, Yodas 93.7%/94.1%. The authors tuned for recall, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- Filtering largely prevents the collapse at 250 distractors (Qwen3-ASR Earnings-21 BWER 15.69% → 11.97%), [arXiv 2608.05759](https://arxiv.org/html/2608.05759)
- Filtering slightly hurts when there are no distractors (Qwen3-ASR Yodas 24.52% → 25.92%) and is expensive: one model call per audio-word pair, [arXiv 2608.05759](https://arxiv.org/html/2608.05759)

**Other retrieval and correction approaches**
- LLM post-correction of named entities using phonetic and semantic matching reports up to 30% relative WER reduction on named entities (search-snippet level), [arXiv 2506.10779](https://arxiv.org/pdf/2506.10779)
- Retrieval front-ends (BR-ASR, GLCLAP) shrink a large list to a top-k per utterance before prompting. Their retrievers are trained, but the principle carries over, [arXiv 2505.19179](https://arxiv.org/pdf/2505.19179); [arXiv 2512.21828](https://arxiv.org/abs/2512.21828)
- OpenAI itself suggests that terminology beyond prompt limits be handled by "post-processing with a text model and checking the results against the audio", [OpenAI speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text)

### Inferences
A harness recipe built from the evidence above (design inference, not tested in any paper):
1. **Unbiased pass.** Run gpt-transcribe with no keywords and Saaras in translit or codemix mode. Keep both outputs; their disagreement is a cheap uncertainty signal.
2. **Find name spans.** Use an LLM, or "contact-call" templates such as "call X", "X ko phone karo", "X ka number".
3. **Retrieve candidates.** Match each span against the contact list on phonetic keys, after transliterating names to a common Roman form (for example Double Metaphone on romanised names, or edit distance over a phoneme transliteration). Keep the top 5–10 using Apple's NPD-style rule.
4. **Biased second pass.** Send only those candidates: gpt-transcribe `keywords`, Saaras v4 `keyterms` (50 maximum), or a text LLM choosing among them.
5. **Verify.** Accept a changed name only if (a) it is phonetically close to the pass-1 span, (b) both ASRs or both passes agree, or (c) an audio LLM answers a forced-choice question ("Which of these names was spoken: A/B/C/none?").

Distractor-aware scoring is the part most specific to this test set. When the top-2 candidates are sound-alikes (small NPD margin), do not trust biased ASR output alone. Use the forced-choice audio check, or show disambiguation in the UI. Always include a "none of these" option to control false positives.

Two mitigations target false positives on utterances with no name: skip pass 2 entirely when no name span is detected (as Hitachi does), and never send keywords "just in case".

### Gaps
- None of the mitigation papers was evaluated on commercial black-box APIs or on Indian or Hinglish phone speech.
- No paper read measured distractor-aware scoring for deliberately confusable sound-alike names. Hitachi reports error-span precision of only 51.9%, so detecting spans is itself noisy.

---

## Q3. OpenAI transcription API (late 2026): gpt-transcribe parameters, logprobs, timestamps, keyword limits, pricing and latency

### Takeaway
`gpt-transcribe` (released 28 Jul 2026) is OpenAI's recommended file-transcription model. It is the only model that accepts `keywords` and the `languages` array, alongside `prompt`. It does **not** return logprobs, and the docs say word or segment timestamps are only supported for `whisper-1`. No keyword-count limit is documented. It costs $0.0045/min. The older models (whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe, gpt-4o-transcribe-diarize) are deprecated but run until 26 Feb 2027, so they remain usable at the hackathon. They are where logprobs (gpt-4o-transcribe and mini) and word timestamps (whisper-1) come from.

### Cited Findings
**Model line-up and dates**
- 28 Jul 2026 changelog: GPT-Transcribe released for file transcription and final transcripts of committed Realtime turns, and GPT-Live-Transcribe for low-latency streaming. "Both models support free-form transcription context, keyword hints, and multiple expected input languages.", [OpenAI changelog](https://developers.openai.com/api/docs/changelog)
- 26 Aug 2026: deprecation of `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` and `gpt-4o-transcribe-diarize`. "These models will shut down on February 26, 2027.", [OpenAI changelog](https://developers.openai.com/api/docs/changelog)
- The 13 Jan 2026 changelog moved `gpt-4o-mini-transcribe` to a 2025-12-15 snapshot and recommended it over `gpt-4o-transcribe`, [OpenAI changelog](https://developers.openai.com/api/docs/changelog)
- `model` accepts `gpt-transcribe`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `gpt-4o-mini-transcribe-2025-12-15`, `whisper-1` and `gpt-4o-transcribe-diarize`, [API reference: create transcription](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)

**`keywords`**
- Optional array of strings: "Words or phrases to guide transcription of the input audio. Supported by gpt-transcribe." No count or length limit is stated, [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
- Rules:
  - Keywords are "hints, not required output."
  - Each keyword must be on one line and cannot contain `<`, `>`, a carriage return or a line feed.
  - The API rejects the entire request if these rules are broken.
  - The guide gives no maximum keyword count or length.

  [OpenAI speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- Over multipart, keywords are sent as repeated `keywords[]` fields, and `languages` likewise as `languages[]` (per the Vercel AI SDK provider docs), [AI SDK OpenAI provider](https://ai-sdk.dev/providers/ai-sdk-providers/openai)
- An open AI SDK issue reported that `languages` and `keywords` passed via `providerOptions.openai` were silently dropped. Whether it is fixed is unconfirmed, [vercel/ai #23487](https://github.com/vercel/ai/issues/23487)

**`languages`, `language` and `prompt`**
- `languages` is an array of expected input languages, with at least one item, supported only by gpt-transcribe. It accepts ISO 639-1 codes, some ISO 639-3 codes and regional `zh` locales. "For gpt-transcribe, languages replaces the singular language field". Do not send both. The response returns the detected `languages` (an empty array when the model cannot predict reliably), [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create); [STT guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- `prompt` is optional free text for style, context or names. It "should match the audio language". It is not supported by gpt-4o-transcribe-diarize, and whisper-1 prompts are capped at 224 tokens. With gpt-transcribe, OpenAI advises combining prompt, keywords and languages, [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create); [STT guide](https://developers.openai.com/api/docs/guides/speech-to-text)

**Logprobs**
- `include: ["logprobs"]` "only works with response_format set to json" and only with `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` and `gpt-4o-mini-transcribe-2025-12-15`. gpt-transcribe is not listed. The response `logprobs` field is an array of `{token, bytes, logprob}`, [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)

**Timestamps**
- `timestamp_granularities` accepts `word` and/or `segment` and requires `verbose_json`. "The timestamp_granularities[] parameter is only supported for whisper-1." Word timestamps add latency. The `verbose_json` response carries `words[{word,start,end}]` and segments with `avg_logprob` and `no_speech_prob`, [STT guide](https://developers.openai.com/api/docs/guides/speech-to-text); [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
- `gpt-live-transcribe` (Realtime) does not return word-level timestamps, speaker labels or confidence scores, [Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)

**Other parameters**
- `chunking_strategy` accepts `"auto"` (loudness normalisation plus voice activity detection) or a `server_vad` object (`prefix_padding_ms` 300, `silence_duration_ms` 200, `threshold` 0.5). If unset, the audio is transcribed as one block. It is required for diarize inputs over 30 s, [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
- `known_speaker_names` and `known_speaker_references` allow up to 4 speakers, with 2–10 s reference clips (diarize model), [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
- `response_format`:
  - gpt-4o-transcribe and mini: `json` only.
  - The diarize model: `json`, `text` and `diarized_json`.
  - The reference does not explicitly list the formats for gpt-transcribe.

  [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
- `stream=true` works with gpt-transcribe, emitting `transcript.text.delta` events and then `transcript.text.done` with the detected languages. whisper-1 does not stream, [STT guide](https://developers.openai.com/api/docs/guides/speech-to-text)
- `temperature` defaults to 0 (auto-raised using log probability up to thresholds), [API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)

**Limits**
- Files up to 25 MB, in flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav or webm. No maximum duration is stated, [STT guide](https://developers.openai.com/api/docs/guides/speech-to-text)

**Realtime transcription**
- Session fields are `transcription.model`, `prompt`, `keywords`, `languages` and `delay` (`minimal`, `low`, `medium`, `high` or `xhigh`, trading latency for accuracy), [Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)
- gpt-live-transcribe does not support `server_vad` or `semantic_vad`, [Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)
- Use gpt-transcribe in Realtime only when transcription should start after a committed turn, or when detected-language output is needed, [Realtime transcription guide](https://developers.openai.com/api/docs/guides/realtime-transcription)

**Pricing (OpenAI pricing page, Standard tier)**

| Model | Price |
|---|---|
| gpt-transcribe | $0.0045/min |
| gpt-live-transcribe | $0.017/min |
| Whisper (whisper-1) | $0.006/min |
| gpt-4o-transcribe | $2.50 in / $10 out per 1M tokens (est. $0.006/min) |
| gpt-4o-mini-transcribe | $1.25 in / $5 out per 1M tokens (est. $0.003/min) |
| gpt-4o-transcribe-diarize | est. $0.006/min |
| gpt-realtime-whisper | $0.017/min |

[OpenAI pricing](https://developers.openai.com/api/docs/pricing)
- Third parties agree on $0.0045/min ($0.27/hour) for gpt-transcribe. One source says batch is not supported for it and another lists a batch price, so batch support is unconfirmed, [LiteLLM model page](https://models.litellm.ai/models/gpt-transcribe)

### Inferences
- The gpt-transcribe baseline exposes no per-word confidence and no timestamps. A harness that needs a confidence signal to decide when to re-bias or verify must get it elsewhere:
  - logprobs from `gpt-4o-mini-transcribe-2025-12-15` (deprecated, but live until Feb 2027);
  - `whisper-1` `verbose_json` (word timestamps, segment `avg_logprob`, `no_speech_prob`);
  - agreement between multiple ASRs or passes;
  - an audio-LLM verification call.
- Because no keyword limit is documented, the "baseline with native keywords" is presumably run with the full 100+ contact list. Q1 evidence suggests that is exactly where over-biasing appears, which gives the harness a concrete failure to beat. The baseline should be measured both with all contacts and with no keywords.
- At $0.0045/min, a few extra passes per utterance cost little. Budget is not the constraint; latency is.

### Gaps
- No official keyword-count or keyword-length limit for gpt-transcribe was found; it may be enforced server-side but is undocumented. Test empirically, for example with 10, 50, 100 and 200 keywords.
- No official latency figures (time-to-first-token or real-time factor) for gpt-transcribe or gpt-live-transcribe were found.
- gpt-transcribe rate limits (RPM) were not found on the pages read.
- The supported `response_format` values for gpt-transcribe are not explicitly documented, and neither is whether `verbose_json` works with it. The guide's statement that timestamps are whisper-1-only implies `verbose_json` word timestamps are unavailable for gpt-transcribe.
- Whether `prompt` and `keywords` interact (for example, whether names in the prompt also bias) is not documented.

---

## Q4. Which OpenAI models accept audio input for chat or reasoning? Can you send a short clip plus a multiple-choice question and get a text answer?

### Takeaway
Audio input is available in Chat Completions through the `gpt-audio` family (`gpt-audio`, `gpt-audio-1.5`, `gpt-audio-mini`) and in the Realtime API (`gpt-realtime`, `-1.5`, `-2`, `-2.1`, `-2.1-mini`). gpt-realtime-2 adds "configurable reasoning". The GPT-5.x reasoning models accept only text and images, and the Responses API docs describe only text and image inputs. Sending a wav or mp3 clip plus a text multiple-choice question through Chat Completions is supported by the documented request shape. Current docs do not explicitly show a text-only (`modalities: ["text"]`) response to audio input, so it must be tested.

### Cited Findings
**Models and dates**
- gpt-audio-1.5 was released to Chat Completions on 23 Feb 2026, alongside gpt-realtime-1.5 in Realtime, [OpenAI changelog](https://developers.openai.com/api/docs/changelog)
- gpt-realtime-2 (7 May 2026) is "a new realtime voice model with configurable reasoning for speech-to-speech agents". gpt-realtime-2.1 and 2.1-mini (6 Jul 2026) bring "improved alphanumeric recognition", [OpenAI changelog](https://developers.openai.com/api/docs/changelog)
- The 22 Sep 2026 changelog entry for the GPT-5.x reasoning models says: "These reasoning models accept text and image inputs and generate text." No 2026 entry adds audio input to them, [OpenAI changelog](https://developers.openai.com/api/docs/changelog)

**gpt-audio-1.5 model card**
- Input: text and audio. Output: text and audio.
- Endpoint: Chat Completions only. Responses, Realtime and Batch are "Not supported".
- 128k context, 16,384 max output tokens, knowledge cutoff 30 Sep 2024.
- Price: $2.50/$10 per 1M text tokens in/out, $32/$64 per 1M audio tokens in/out.
- Default rate limits: 5,000 RPM / 450k TPM at the Build tier.

[gpt-audio-1.5 model page](https://developers.openai.com/api/docs/models/gpt-audio-1.5)

**Request shape**
- The Audio in Chat Completions guide says to "include audio in the modalities array and use an audio model, like gpt-audio-1.5". Audio goes in an `input_audio` content part with base64 `data` and a `format`. Every example on that page uses `modalities: ["text","audio"]`, [Audio in Chat Completions guide](https://developers.openai.com/api/docs/guides/audio-chat-completions)
- In the Chat Completions reference:
  - `modalities` defaults to `["text"]` ("Most models are capable of generating text, which is the default").
  - `input_audio.format` "Currently supports "wav" and "mp3"".
  - The `audio` output parameter is required only when audio output is requested.

  [Chat Completions API reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- The Responses API docs "currently describe text and image inputs with text outputs"; for audio chat, use Chat Completions, [Audio in Chat Completions guide](https://developers.openai.com/api/docs/guides/audio-chat-completions)

**Pricing per 1M tokens (OpenAI pricing page)**

| Model | Audio in | Audio out | Text in | Text out |
|---|---|---|---|---|
| gpt-audio | $32 | $64 | $2.50 | $10 |
| gpt-audio-mini | $10 | $20 | $0.60 | $2.40 |
| gpt-realtime-2 / 2.1 | $32 | $64 | $4 | $24 |
| gpt-realtime-2.1-mini | $10 | $20 | $0.60 | $2.40 |

[OpenAI pricing](https://developers.openai.com/api/docs/pricing)

### Inferences
- A clip-plus-multiple-choice verifier ("Audio: <clip>. Which contact was named? A) Rohit B) Rohan C) Mohit D) none") is feasible with `gpt-audio-1.5` or `gpt-audio-mini` in Chat Completions. Send the cropped clip as wav or mp3 base64 with the text question. Omitting `modalities` (default `["text"]`) should give a text-only answer. That behaviour matches earlier gpt-4o-audio-preview usage from prior knowledge, but it was not confirmed on the current pages and must be smoke-tested first. Fallback: request `["text","audio"]` and read only the text part.
- gpt-audio-mini ($10 per 1M audio input tokens) is the cheapest option for per-candidate yes/no checks, à la Huber & Waibel. Collapsing the check into a single multiple-choice call per span is cheaper than one call per candidate, and the "none" option directly targets false positives.
- Cropping the clip needs timestamps. Since gpt-transcribe has none, use whisper-1 word timestamps or Sarvam chunk timestamps (see Q5), or send the whole short utterance, which is fine for phone commands of a few seconds.

### Gaps
- Not confirmed from current official docs: that `modalities: ["text"]` with `input_audio` is accepted by gpt-audio-1.5 or gpt-audio-mini; maximum audio duration or size per Chat Completions request; audio tokens per second (needed for exact cost); whether `logprobs` works with gpt-audio models (useful for multiple-choice confidence).
- Whether gpt-realtime-2 sessions can be set to text-only output in response to audio was not confirmed; the Realtime transcription guide does not cover it.

---

## Q5. Sarvam API (Saaras v3/v4): endpoint, parameters, biasing support, output script for Hinglish, timestamps, pricing, rate limits

### Takeaway
The REST endpoint is `POST https://api.sarvam.ai/speech-to-text` (multipart, `api-subscription-key` header). It now **defaults to `saaras:v4`**, and `saaras:v3` is "legacy". The only biasing feature is **`keyterms`**: up to 50 terms of 64 characters or fewer, **saaras:v4 only**. There is no prompt or context parameter, and Saaras v3 has no documented biasing at all. Modes are transcribe (native script, i.e. Devanagari for Hindi), translate (English), verbatim, translit (all Roman) and codemix (English words in Latin, Hindi in Devanagari). Timestamps are chunk-level only; word level is not supported. REST takes clips under 30 s. Pricing is about ₹0.49/min pay-as-you-go, and REST is limited to 60 requests/min on that tier.

### Cited Findings
**REST endpoint and parameters**
- Request: `POST https://api.sarvam.ai/speech-to-text`, `multipart/form-data`, with an `api-subscription-key` header, [Sarvam API reference: transcribe](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)
- `file` accepts WAV, MP3, AAC, AIFF, OGG, OPUS, FLAC, MP4/M4A, AMR, WMA, WebM and PCM. Audio is merged to mono, and the API "works best with audio files sampled at 16kHz". PCM needs `input_audio_codec` and must be 16 kHz, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)
- `model` defaults to `saaras:v4` (recommended); `saaras:v3` is legacy. `saarika:v2.5` is no longer listed on that page, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe); [Saaras model page](https://docs.sarvam.ai/api/getting-started/models/saaras/llms.txt)
- `mode` (v3/v4, default `transcribe`):
  - `transcribe`: native script, normalised numbers.
  - `translate`: English.
  - `verbatim`: word for word, no normalisation.
  - `translit`: Roman script.
  - `codemix`: English words in Latin, Indic words in native script.

  [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)
- `language_code` takes BCP-47 codes such as `hi-IN` or `en-IN` (23 options). `unknown` triggers auto-detection and returns `language_probability`. On the realtime WebSocket the auto value is `auto`, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe); [Sarvam language codes how-to](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/how-to/specify-language-codes)
- `with_timestamps` returns chunk-level timestamps: "each entry covers a sentence or phrase, not an individual word". Word-level timestamps are not supported, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)
- `keyterms`:
  - Up to 50 terms, each 64 characters or fewer, sent as a JSON array in one field.
  - Supported only with `saaras:v4`.
  - "Keyterms bias recognition, they do not guarantee that a term will appear in the transcript."
  - The page says not to use the older `keyterm` or `hotwords` fields.
  - There is no prompt or context parameter.

  [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)
- Response fields are `request_id`, `transcript`, `language_code`, optional `timestamps{words, start_time_seconds, end_time_seconds}` and `language_probability`. Errors are 400, 403, 429, 500 and 503, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)
- Diarization is Batch-only. REST handles clips under 30 s, and Batch handles up to 2 h per file, [Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe); [Saaras model page](https://docs.sarvam.ai/api/getting-started/models/saaras/llms.txt)

**Keyterms details**
- Keyterms are available on REST, Batch and both WebSocket APIs (legacy `/speech-to-text/ws` and realtime `/speech-to-text-realtime/ws`), with `saaras:v4` only.
- Requests with more terms fail with the error "At most 50 keyterms are allowed".
- Multi-word phrases go in one list item; do not send comma-separated terms in one string.
- Script guidance: use `codemix` if a Latin-script keyterm such as "PhonePe" must stay Latin.
- There is no guidance on how many terms to use or how to spell names, and no over-biasing warning.

[Sarvam keyterms how-to](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/how-to/keyterms)
- A September 2026 docs changelog notes saaras:v4 is now on the Realtime API (search-snippet level), [Sarvam changelog 2026-09-03](https://docs.sarvam.ai/changelog/2026/9/3.md)

**Streaming**
- The legacy WebSocket `/speech-to-text/ws` defaults to v4 and also accepts v3, [Sarvam streaming API](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/streaming-api)
- The realtime `/speech-to-text-realtime/ws` defaults to `saaras:v3-realtime`, with v4 also available. Parameters include `language_code` (required), `endpointing` (vad or manual), `min_speech_duration_ms` (default 250) and `stream_type` (fast, balanced or simulated), [Sarvam realtime streaming](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-streaming)

**Hinglish output script**

| Mode | Output |
|---|---|
| `transcribe` | Hindi in Devanagari |
| `codemix` | English words in Latin, Hindi in Devanagari |
| `translit` | Whole utterance in Roman script |

These are v4 examples; the docs do not show v3's rendering separately. [Saaras model page](https://docs.sarvam.ai/api/getting-started/models/saaras/llms.txt)

**Saaras v4 model facts**
- The v4 blog describes a 3B hybrid state-space-model LLM decoder trained from scratch, and five output formats, [Sarvam blog: Introducing Saaras v4](https://www.sarvam.ai/blogs/introducing-saaras-v4)
- Secondary coverage reports a company-stated 16.03% WER in a keyword-prompting setting on IndicContextEval. This is a company-reported benchmark, not independently verified, [AlphaSignal](https://alphasignal.ai/news/sarvam-s-saaras-v4-brings-all-22-indian-languages-into-one-asr-model)

**Pricing and rate limits (Sarvam pricing doc)**

| | Pay as you go | Pro | Growth |
|---|---|---|---|
| Speech to Text (real-time, streaming, batch), per min | ₹0.49 | ₹0.45 | ₹0.41 |
| With diarization (batch), per min | ₹0.59 | ₹0.54 | ₹0.50 |
| Real-time REST rate limit | 60 req/min | 100 req/min | 4,000 req/min |
| WebSocket concurrency | 20 | 100 | 100 |
| Batch rate limit | 20 req/min | 100 req/min | 500 req/min |

- Prices exclude GST and are billed per second.
- New verified users get ₹100 of free credits.

[Sarvam pricing](https://docs.sarvam.ai/api/getting-started/pricing)
- Conflicting price figures: older docs pages list ₹30/hour (₹45/hour with diarization), and some Sarvam marketing pages show ₹1.25/min. The per-minute pricing doc above is treated as current, [Sarvam pricing (older .md)](https://docs.sarvam.ai/api/pricing.md); [Sarvam speech-to-text Hindi page](https://www.sarvam.ai/apis/speech-to-text/hindi)

### Inferences
- The "Saaras v3 as Equal uses it" baseline has **no** context biasing available through the documented API. Any contact-name improvement over it must come from the harness: retrieval and post-correction, or switching to v4 with keyterms.
- `keyterms` caps at 50, below the 100+ contact list, so a v4-with-keyterms comparison is forced into per-utterance retrieval and shortlisting anyway. That matches the mitigation evidence in Q2.
- Script consistency matters for matching names:
  - Equal-style `translit` gives Roman output, which is easiest to fuzzy-match against a Roman contact list.
  - `transcribe` gives Devanagari, which needs transliteration before matching.
  - Keyterms written in Roman may behave differently in `transcribe` mode than in `codemix` or `translit` mode. This is untested; try both.
- At ₹0.49/min and 60 REST requests/min on pay-as-you-go, ₹100 of free credit buys about 200 minutes of audio. That is enough for a hackathon eval set, but the 60 RPM limit means throttling batch evals.
- Sarvam timestamps are phrase-level, so they cannot localise a single name for clip cropping.

### Gaps
- No documented prompt or context parameter exists for Saaras v3 or v4; older Saaras versions had a `prompt` field on the translate endpoint, but current docs do not list one. Whether v3 silently ignores `keyterms` or rejects it: docs say the error is "'keyterms' is only supported by model 'saaras:v4'", i.e. rejected.
- No official latency numbers for Saaras v3 or v4 REST were found.
- No official per-model price difference between v3 and v4 was found.
- No v3-specific WER figures or v3-versus-v4 Hinglish rendering differences were found in the docs read.

---

## Q6. Does Equal AI publicly describe any context or biasing layer on top of Saaras?

### Takeaway
No. Sarvam's official case study says Equal uses **Saaras V3 as its primary model (about 85% of its speech-recognition calls)**, mostly in **translit mode (about 97% of calls, Roman-script output)**. It describes no prompts, keyword biasing, custom vocabulary, contact-list context or post-processing layer, and it reports no accuracy (WER) figures.

### Cited Findings
- Equal "now runs Saaras V3, Sarvam's speech recognition model as the primary model", and it accounts for about 85% of Equal's speech-recognition calls, [Sarvam customer story: Equal](https://www.sarvam.ai/stories/equal)
- Transliteration is the dominant mode at about 97% of calls, converting Indian-language speech to Roman script. Transcription, translation, code-mix and verbatim modes are used where needed. The workload covers standard transcription, real-time streaming, bulk batch and speaker diarization, [Sarvam customer story: Equal](https://www.sarvam.ai/stories/equal)
- Scale and reliability:
  - Over a million live calls per day across nine Indian languages, and about 34 million audio minutes per month.
  - Volume grew about 420x from October 2025 to May 2026 (555k to 234M calls), with a June 2026 run rate of about 285M calls per month.
  - 99.98% success rate over about 129M calls in a 30-day window.

  [Sarvam customer story: Equal](https://www.sarvam.ai/stories/equal); repeated by [AlphaSignal](https://alphasignal.ai/news/sarvam-s-saaras-v3-powers-equal-ai-s-285m-monthly-indian-calls)
- No latency figures; calls must be handled "within seconds". No WER or accuracy metrics. No mention of context, prompts, keyword biasing, custom vocabulary or post-processing; downstream systems consume the Roman-script output directly, [Sarvam customer story: Equal](https://www.sarvam.ai/stories/equal)

### Inferences
- The realistic Sarvam baseline is `saaras:v3` with `mode=translit` and no biasing, since that is what Equal documents and v3 has no biasing feature. Equal may well have internal post-processing (for example, matching against a user's contacts), but nothing public says so. Do not claim either way.
- "Over a million live calls per day" (about 30M+ per month) and "285M calls per month" are hard to reconcile, unless "calls" means API calls (one phone call making many STT requests) rather than phone calls. Treat the volume figures as marketing-level.

### Gaps
- Equal AI's own website or engineering blog was not searched. Only Sarvam's case study and a secondary write-up were found. Equal may describe its pipeline elsewhere, for example in talks or job posts; this was not found.
