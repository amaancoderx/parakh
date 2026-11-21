# Contextual biasing and hotword harnesses in Chinese, Japanese and Korean ASR: what produced measured gains, and what an API-only harness (Parakh) can copy

Scope note: covers 2022–2026 CJK work. Status labels: [peer-reviewed], [preprint], [vendor doc], [snippet-only] (seen only in a search-result summary, page not opened). Earlier research already covered RECOVER, DeRAGEC, Apple contact retrieval, Hitachi selective retrieval and Huber & Waibel; this file does not repeat them. Parakh context: it fuses Sarvam Saaras v3/v4 and gpt-transcribe, finds name-like spans where they disagree, retrieves candidates by phonetic similarity, re-runs gpt-transcribe with a short `keywords` hint list (including "rival" spellings), votes over shuffled hint orders, and writes a name only if the audio backs it.

---

## 1. FunASR / Paraformer / SeACo-Paraformer hotword customisation, and commercial hotword APIs (Alibaba Cloud, Tencent Cloud, iFlytek)

### Takeaway
Alibaba's SeACo-Paraformer gets its hotword gains from two things a black-box harness can copy. First, it filters in two stages: it scores the whole list cheaply, then biases with only the top-k. Second, it has an explicit "no-bias" outcome, so it can decline every hotword. Commercial CJK APIs all cap list sizes (500–2,000), use tiered weights, and warn that high weights replace similar-sounding words. Tencent's "weight 100" mode is a vendor-built homophone replacement, which shows the risk of post-hoc phonetic substitution.

### Cited Findings
**SeACo-Paraformer (Alibaba DAMO; ICASSP 2024 [peer-reviewed], arXiv 2308.03266)**
- Architecture: a bias encoder (2-layer LSTM, 512 units, shared embedding) encodes the hotword list. A bias decoder (4-layer Transformer) attends over the CIF acoustic output and the decoder state. The Paraformer backbone is frozen, and only the bias modules are trained, on randomly sampled hotwords, [SeACo-Paraformer](https://arxiv.org/html/2308.03266v4)
- **No-bias label:** an extra output token "#" marks non-hotword positions. At inference, if the bias decoder's argmax is "#", the plain ASR distribution is used unchanged. Otherwise the output is λ·P_bias + (1−λ)·P_ASR, with λ = 1.0 in the experiments, [SeACo-Paraformer](https://arxiv.org/html/2308.03266v4)
- **Attention Score Filtering (ASF), a two-stage design:** (1) run the bias decoder with the full list; (2) sum each hotword's last-layer attention scores over output steps; (3) keep the top **k = 50** and run the bias decoder again with only those, [SeACo-Paraformer](https://arxiv.org/html/2308.03266v4)
- Recall gains: on the industrial test sets, average R1-hotword recall goes from 12% (no biasing) to 51% (CLAS), 60% (SeACo) and 65% (SeACo+ASF). On open-source AISHELL-1-NE it goes 69% (CLAS) → 79% (SeACo) → 87% (SeACo+ASF). That is a 30.2% relative CER reduction and a 26.1% relative recall gain over CLAS. A hotword counts as recalled only if it is predicted in full, [SeACo-Paraformer](https://arxiv.org/html/2308.03266v4)
- List-size scaling: the Test-Entity list was grown from 231 to 400, 800, 1,200, 2,000 and 4,000 hotwords. All models degrade as the list grows, and only SeACo+ASF still reduces CER at 4,000. The paper reports no precision, false-trigger or U-CER figures (recall only), [SeACo-Paraformer](https://arxiv.org/html/2308.03266v4)

**H-PRM, a pluggable hotword pre-retrieval module (CIKM '25 [peer-reviewed], arXiv 2508.18295)**
- It matches hotwords to the **ASR output text in phoneme space**, not to the raw audio. Hotwords and the transcript are converted to pinyin/phoneme embeddings with the SAM-BERT frontend. A cosine-similarity matrix per hotword is scored by a small binary CNN, and the top-N hotwords are passed downstream. Phoneme-to-phoneme matching beat audio-to-audio (KWS-Whisper), text-to-text (RoBERTa) and audio-to-text (Qwen2-Audio, R@50 only 9.48% / 3.25%), [H-PRM](https://arxiv.org/html/2508.18295v1)
- On Common-Voice-zh with a 3,800-hotword list, SeACo-Paraformer MER/PRR goes from 9.45/70.63 to 6.57/93.90 with H-PRM. Without H-PRM, SeACo's PRR fell from 94.6% to 71.9% as distractors grew to 3,800. With H-PRM it stayed around 93%, [H-PRM](https://arxiv.org/html/2508.18295v1)
- **Prompt-based recognisers need very short lists.**
  - Whisper-small was best at about top-3. At top-50, PRR fell to 53.3 and MER rose to 20.79.
  - Qwen2-Audio-Instruct was best at **top-1** (MER 3.24). At top-50, MER reached **29.42** and PF1 fell to 56.0.
  - The authors say prompting "may not be the ultimate solution."
  - Caveat: some numbers in the paper's text do not match its tables (e.g., Whisper CV-zh MER 18.65→12.46 in the text vs 21.20→16.40 in Table 2), [H-PRM](https://arxiv.org/html/2508.18295v1)

**FunASR runtime (open source) [vendor doc]**
- Hotword file format: one `hotword weight` per line (example "阿里巴巴 20"). Recommendation: "建议热词长度不超过10，个数不超过1k，权重1~100". Server-side hotwords (`--hotword`) apply globally, client hotwords apply only to that client, and the two are merged. 2pass-offline gained WFST hotwords plus n-gram LM decoding in Jan 2024. A separate neural-hotword model, `speech_paraformer-large-contextual`, is listed, [FunASR SDK advanced guide](https://github.com/alibaba-damo-academy/FunASR/blob/main/runtime/docs/SDK_advanced_guide_online_zh.md)

**Alibaba Cloud Model Studio / Bailian (Paraformer, Fun-ASR, Qwen-ASR) [vendor doc]**
- **Per-request vs persistent lists:** "instant hotwords" (即时热词) are passed per request as `{text: weight}`. "Precompiled hotwords" are created once and referenced by `vocabulary_id`. The list's `target_model` must match the recognition model, [Alibaba improve-asr-accuracy](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)
- **Tiered weights (1–5, start at 4):**
  - 1–2: weak bias, for **terms that sound like common words**.
  - 3–4: most cases.
  - 5: frequent terms that are rarely confused.
  - A "super hotword" weight of 50 exists on Qwen-ASR, capped at 50 entries.
  - Warning: overly high weights cause similar-sounding words to be wrongly replaced by the hotword, [Alibaba improve-asr-accuracy](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)
- **Limits:**
  - Hotwords per list or request: 2,000 for Qwen-ASR and Fun-ASR main models; 500 for other Fun-ASR models and Paraformer.
  - If precompiled plus instant hotwords exceed 2,000 on Qwen-ASR, 2,000 are chosen **at random**.
  - Text length: 15 characters for non-ASCII text; 7 space-separated segments for ASCII.
  - Wait at least 5 minutes after updating a list.
  - Account quota conflicts: this page says 50 precompiled lists per account, while the SDK page says 10 lists of up to 500 words each, [Alibaba improve-asr-accuracy](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy); [Alibaba vocabulary SDK](https://help.aliyun.com/zh/model-studio/vocabulary-python-sdk)
- **Context enhancement (上下文增强):** the alternative to hotwords. You pass conversation history or domain text, which must contain the correct spelling. Only the last 5 rounds are kept, with ≤400 characters per round, and excess text is silently truncated.
  - Official troubleshooting advice: **compare the same audio with and without the feature**.
  - Paraformer is not listed for instant hotwords or context enhancement, [Alibaba improve-asr-accuracy](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)
- Older Alibaba products accept **negative weights** of [-6, 5] to suppress words: ICE/IMS hotword struct, and Tingwu (300 hotwords per list, ≤10 characters). Values >0 raise the probability of recognition and values <0 lower it [snippet-only], [Alibaba ICE Hotword struct](https://help.aliyun.com/zh/ims/developer-reference/api-ice-2020-11-09-struct-hotword); [Tingwu overview](https://help.aliyun.com/zh/tingwu/overview)
- Older NLS docs split hotwords into "name-class" (person names **or** place names, one class per list) and "business-class" lists [snippet-only], [Alibaba ISI customization doc](https://help.aliyun.com/zh/isi/developer-reference/use-customization-tools-for-speech-recognition)

**Tencent Cloud ASR [vendor doc; pages failed to open (SSL), content from search snippets]**
- Weights are integers in [1, 11] or 100. **11 = "super hotword"**, and Tencent advises using 11 only for important, must-hit words, because too many 11-weight words lower overall character accuracy. Limits: 30 lists by default, 1,000 words per list, ≤10 Chinese characters or 30 English characters per word [snippet-only], [Tencent ASR hotword API](https://cloud.tencent.com/document/api/1093/41111)
- **Weight 100 = "enhanced hotword"**: homophones of the hotword are **replaced** (同音替换), Mandarin only (8k_zh/16k_zh, `reinforce_hotword`). When two hotwords share the same pronunciation, the one with the higher weight wins [snippet-only; exact page unverified], [Tencent Smart Subtitle hotwords](https://www.tencentcloud.com/document/product/1041/68176); [Tencent ASR hotword API](https://cloud.tencent.com/document/api/1093/41111)
- Sources conflict on the range: the Smart Subtitle/console docs give 1–10 in `word|weight` format, [Tencent live subtitle hotwords](https://www.tencentcloud.com/zh/document/product/267/78638)

**iFlytek**
- No primary documentation on hotword list size or weights was found (see Gaps).

### Inferences
- **Two-stage shortlist (SeACo ASF, H-PRM):** score the whole context list cheaply (phonetic match against all three recognisers' outputs), then send only a tiny shortlist to the recogniser that takes hints. H-PRM's prompt-based results (Whisper best at about 3 hints, Qwen2-Audio at 1, and MER 3.24 → 29.42 at 50 hints) are the strongest direct evidence that gpt-transcribe's `keywords` list should stay at about 1–5 entries per span.
- **Keep a "no-bias" outcome:** the voting should always keep the no-hint transcript as a full candidate. SeACo's "#" token shows a production system that is explicitly allowed to use no hotword at all.
- **Tiered caution, per Alibaba's 1–2 weight rule:** names that are also common words should need stronger audio evidence before acceptance. Hindi examples include Pooja/puja (worship), Kamal (lotus), Suraj (sun) and Asha (hope). The API cannot weight hints, but the harness can raise the acceptance threshold for these.
- **Tencent's weight-100 mode** is pinyin-level homophone replacement. Tencent restricts it to Mandarin and keeps it opt-in, which suggests that unconditional phonetic replacement is too risky as a default. That supports Parakh's audio-check step.
- **Random truncation:** Alibaba truncates over-long hotword lists and context text silently and at random. Parakh should never rely on a vendor-side cap; it should cap its own lists.

### Gaps
- SeACo's exact Figure 2 values (CER vs list size up to 4,000) and any SeACo false-trigger or precision numbers were not in the extracted text.
- iFlytek's hotword limits and weights: no primary documentation found. A third-party mirror mentions only self-training corpus limits (≤42 characters per line, ≤1 MB).
- Tencent pages could not be opened (SSL errors), so the exact `hotword_list` (temporary per-request) format and limits are unverified.
- No vendor publishes precision or false-trigger rates for their hotword features.

---

## 2. WeNet / k2 / icefall / sherpa-onnx context graphs: backoff that cancels partial matches, boosting scores, false-alarm evidence

### Takeaway
All three toolkits pay the hotword bonus token by token as a prefix matches. If the full phrase is not completed, a failure arc **takes the accumulated bonus back**, so partial matches never keep credit. The post-hoc equivalent is that a hint counts only if the whole name is matched; a prefix-only or merged match is reverted. Public numbers on false alarms for these graphs are essentially absent.

### Cited Findings
- **sherpa-onnx (k2-fsa):**
  - Hotwords are tokenized into an **Aho-Corasick automaton**: goto arcs carry matches, failure arcs handle mismatches, and output arcs mark full matches.
  - The boost is spread evenly along the path. Each state has a node score (used for cancellation) and an output score (the total for full matches ending there).
  - The boost is granted as soon as a partial sequence matches. If the path fails to complete a hotword, the partial boost is removed. Example: the 4-point node score for "SHEL" is cancelled when "F" fails to match in "SHELF". The "HI" example cancels its partial boost on finalize, which returns the graph to the root at the end of decoding.
  - Per-phrase scores use `phrase :3.5` syntax. The global `hotwords-score` default appears to be 1.5.
  - Requires `modified_beam_search` (not greedy) and transducer models. Units are `cjkchar`, `bpe` or `cjkchar+bpe`.
  - No recall, precision or false-alarm metrics are published; only before/after examples, [sherpa-onnx hotwords](https://k2-fsa.github.io/sherpa/onnx/hotwords/index.html)
- **WeNet:**
  - Biasing is shallow fusion: y* = argmax log P(y|x) + λ log P_C(y), for CTC prefix beam search and WFST beam search.
  - Each character gets a reward (example: 0.25 per character). A failure arc removes the boosted score when a prefix matches early but the full phrase does not.
  - **Only one hotword can be matched at a time**; another can start only after the current one succeeds or fails.
  - Start/end boundaries are tagged (`<context>cat</context>`).
  - A pruning fix subtracts backoff-returned cost before pruning, because accumulated backoff cost otherwise distorts beam pruning.
  - Example `--context_score 3`. No CER, recall or false-alarm results are given, [WeNet context biasing](https://wenet-e2e.github.io/wenet/context.html)
- **icefall `context_graph.py`:** an Aho-Corasick phrase-boosting tree for RNN-T shallow fusion. Fail arcs "subtract the accumulated score in the case of the absence of the required transition", and per-phrase `context_score` is supported, [Idiap TSD 2025 / arXiv 2409.13514](https://arxiv.org/html/2409.13514v2)
- NVIDIA's TurboBias critiques icefall for spreading weight uniformly and giving the full accumulated reward only at the final node, which it says is inefficient for greedy search [preprint; snippet-only], [TurboBias](https://arxiv.org/html/2508.07014v2)
- Related Mandarin work by Yang, Sun, Wang, Zhang, Ma and Lei Xie [Interspeech 2023, peer-reviewed; affiliations not verified]:
  - "Two-stage contextual word filtering" first computes a **posterior-sum confidence that ignores phone order**, then a **sequence-order confidence** on the survivors, before attention-based biasing.
  - It reports about 20% CER reduction on large-list music search and about 40% on small-list contacts. Two stages beat PSC-only, [Yang et al. 2023](https://arxiv.org/abs/2301.06735)
- **Production analogue (Naver CLOVA, Korean) [vendor doc]:** multi-word boost phrases are affected mainly when the phrase appears whole, and a sentence containing only part of a longer boosted compound is unlikely to be affected, [CLOVA Speech API](https://api.ncloud-docs.com/docs/ai-application-service-clovaspeech-longsentence)

### Inferences
- **The cancellation logic:** give provisional credit while evidence accumulates, and take it all back if the full unit never completes. This prevents a hotword's first syllables from pulling an ordinary word toward the hotword. A post-hoc acceptance rule for Parakh along the same lines:
  - (a) Accept a hinted name only if the hinted re-run contains the **complete** candidate name, all aksharas or syllables, aligned to the disputed span.
  - (b) Revert if the re-run shows only a prefix (e.g., "Rajes" for "Rajesh Kumar") or if the name swallowed neighbouring words.
  - (c) Revert if the no-hint recognisers do not support the remaining syllables.
- **WeNet's "one hotword at a time" rule** suggests resolving one disputed span per cross-examination call. Do not let several hints compete inside a single span.
- **Per-token rewards favour long names.** If Parakh scores candidates by summed phonetic matches, normalise by length; VISH, in Q6, normalises by aligned frames.
- **The two-stage PSC→SOC filter** maps to: first a bag-of-phonemes overlap (cheap, order-free) over the whole context list, then an order-aware alignment (Smith-Waterman or edit distance) on the survivors.

### Gaps
- No paper or doc found reporting false-alarm rates for icefall, sherpa-onnx or WeNet context graphs, or how false alarms vary with `context_score`.
- Recommended score ranges are not documented beyond examples (1.5, 3).

---

## 3. Chinese named-entity and pinyin/tone-based phonetic retrieval for ASR error correction

### Takeaway
Across 2023–2026 Chinese work, the winning retriever compares **phonemes or pinyin** of candidate entities against **the ASR text**, using normalised edit distance or local alignment, taking the best score over all N-best hypotheses and keeping a **small k (3–10)**. Pure phonetic retrieval breaks down when the list contains homophones (it made NE errors worse on a homophone-heavy set) and on loanwords. The fixes that worked were a semantic or description tie-breaker, an N-best agreement rejection test, and audio-based verification.

### Cited Findings
- **DANCER (National Taiwan Normal University + E.SUN; arXiv 2403.17645; venue not verified):**
  - The PED-NEC baseline retrieves entities by **pinyin + normalised edit distance** from a 16,168-entity list.
  - On AISHELL-1, PED-NEC improves NE-CER from 11.12 to 8.14.
  - **On the 115-utterance Homophone test set, PED-NEC makes things worse:** NE-CER rises from 15.58 to 20.88 and NE recall falls from 70.25 to 56.72.
  - DANCER adds entity descriptions plus a dense retriever (α = 0.6 phonetic vs semantic, **top-k = 10**) and gets NE-CER 11.33 / recall 79.84 there. That is a 46% relative NE-CER reduction vs PED-NEC on Homophone and about 7% on AISHELL-1.
  - The PED-NEC vs DANCER gap widens as the entity list grows, [DANCER](https://arxiv.org/abs/2403.17645)
- **DANCER's N-best rejection rule:**
  - Reject(e) = Σ_n p_n · ED(Pin(e_n), Pin(e)), where e_n is the aligned span in each N-best hypothesis and p_n is that hypothesis's beam score.
  - The correction is rejected if its rejection score is higher than the original span's, i.e. "it might deviate from the original audio".
  - Without rejection, non-entity CER rises from 4.00 to 4.64 on AISHELL-1 and from 5.30 to 6.12 on Homophone, [DANCER](https://arxiv.org/abs/2403.17645)
- **RASTAR [preprint, arXiv 2602.12287]:**
  - Pipeline: entity detection, then pinyin normalised-edit-distance retrieval (following PED-NEC), then LLM correction with adaptive chain-of-thought (Qwen3 8B/0.6B, DPO).
  - They chose **k = 3** "as an excessively large k would introduce irrelevant or weakly related entities, interfering with the model's correction performance". Repository: 16,168 entities.
  - Homophone set, NE-CER: DANCER 11.33, Qwen3-8B thinking 8.14, RASTAR-8B 7.43. NE recall 85.80 vs 79.84.
  - AISHELL-1 NE recall: 89.33 vs DANCER 85.84, [RASTAR](https://arxiv.org/abs/2602.12287)
- **JSPG (Soochow University) [preprint, arXiv 2605.16896]:**
  - Fuses a semantic score (Qwen3-Embedding over concatenated N-best) with **pinyin + glyph similarity**. These are extended to sequence level with an **extended Smith-Waterman local alignment**, taking the **maximum over the N-best list**. Pinyin is used as complete sequences with tones (e.g., yu3) and normalised Levenshtein distance.
  - The authors state that pinyin alone "introduces substantial noise, as it retrieves many irrelevant characters alongside the correct keyword". This is a qualitative claim, not quantified.
  - **K = 10** gave the best downstream results in most settings.
  - Fusion weights: α = 0.7 pinyin vs glyph gives R@100 99.13; β = 0.4 semantic weight gives R@1 64.52.
  - ICI set with LLM-Refine (GPT-OSS-120B prompted with retrieved keywords): K-CER 30.7 → 4.85 and recall 40.8 → 93.2, with U-CER (non-keyword) roughly stable, [JSPG](https://arxiv.org/html/2605.16896v1)
- **H-PRM:** phoneme embeddings of ASR text vs hotwords beat audio-based and text-based matching for retrieval (see Q1), [H-PRM](https://arxiv.org/html/2508.18295v1)
- **Generative Annotation NEC (Huawei Translation Services Center) [preprint, arXiv 2508.20700]:**
  - Phonetic edit-distance NEC fails when the transcript looks very different from the entity, as with loanwords and English inside Chinese (e.g., ChatGPT → "切特GPD", Midjourney → "米德仲尼").
  - Fix: entity audio is synthesised with TTS and stored. A classifier scores whether a speech segment contains each entity, keeping candidates with probability >0.3 (up to 5 per segment). The generator can output "<empty>" to reject.
  - BuzzWord set NE recall: Whisper 12.22 → PED-NEC 61.82 → proposed 87.47.
  - Commercial engines on BuzzWord: iFlytek 19.18 → 46.42 → 81.71; Amazon 9.84 → 39.36 → 80.02.
  - Overall CER was worse than PED-NEC on BuzzWord (14.77 vs 10.67), [Generative Annotation NEC](https://arxiv.org/html/2508.20700v2)
- **PARCO (Nagoya University + CyberAgent) [preprint, arXiv 2509.04357]:**
  - Model: a phoneme-enriched entity encoder, a contrastive loss with phonetically similar hard negatives, and inference-time hierarchical entity filtering (phoneme-level retrieval plus confidence gating).
  - AISHELL-1 NE-CER with 1,000 distractors: Conformer 9.60, CopyNE 3.76, PARCO 2.84.
  - Ablation at 5,000 distractors: removing the phoneme encoder raises NE-CER from 3.56 to **8.27**; removing filtering raises it to 4.07, [PARCO](https://arxiv.org/html/2509.04357v1)
- **PAC (ICASSP 2026 per VISH's reference list):** interleaves grapheme and phoneme forms of the context words in the LLM prompt, and trains with RL on homophone-swapped distractors. It reports a 60.5% relative biased-WER cut on AISHELL-1 vs strong baselines [abstract-level only], [PAC](https://arxiv.org/html/2509.12647v1)
- **PY-GEC (Huawei) [preprint, arXiv 2409.13262]:** feeding the 1-best text **plus its pinyin** to an LLM corrector, with multitask pinyin↔text training, gives 8.3% relative CER reduction and +3.9% relative entity recall vs direct correction, [PY-GEC](https://arxiv.org/html/2409.13262). Tencent's ChineseHP work argues that pinyin derived from a hypothesis has a lower error rate than the hypothesis text itself, [Pinyin Regularization](https://arxiv.org/abs/2407.01909)
- **CTC-assisted LLM contextual ASR (SJTU X-LANCE + Alibaba; SLT 2024):** filters a large bias list by **matching against a coarse CTC hypothesis** and puts only the survivors into the LLM prompt. LibriSpeech results: 1.27/3.67 WER/B-WER (test-clean), 2.72/8.02 (test-other) with 100 words, and still strong with 2,000 words. English only, [CTC-Assisted](https://arxiv.org/html/2411.06437v1)
- Kong et al. [preprint, arXiv 2512.21828] combine GLCLAP-based retrieval with "fuzzy matching" to pick a compact top-k, then prompt an LLM-ASR trained with GRPO. No numbers were on the abstract page, [Kong et al.](https://arxiv.org/abs/2512.21828)

### Inferences
- **Representation:** the best-performing retrievers compare phonetic keys of candidates against **text from every hypothesis** (max over N-best, as in JSPG and DANCER), with local alignment (Smith-Waterman) so a name can be found inside a longer, mis-segmented span. For Hindi/Hinglish, a romanised phonetic key with schwa-deletion normalisation, compared across all three recognisers' outputs, is the closest analogue to "pinyin over N-best". Treating Parakh's three recognisers as an N-best is directly supported.
- **Retrieval size:** k = 3 (RASTAR), k = 10 (DANCER, JSPG) and top-1 to 3 for prompt-based recognisers (H-PRM). Parakh's short hint list is consistent with all of these.
- **Homophone trap:** when two context names share a phonetic key, phonetic retrieval alone **increases** NE errors (DANCER's Homophone set). Parakh's order-shuffled voting addresses this, but the CJK fixes add a second, non-phonetic signal: a description or semantic fit (DANCER, JSPG) or glyph (JSPG). In the Hindi setting this could be relationship or context-list metadata (e.g., which names co-occur in this caller's history).
- **N-best rejection test, copyable almost verbatim:** compute the phonetic distance from the proposed name to each recogniser's aligned span, weighted by recogniser reliability, and compare it with the same score for the original span. Reject if the proposal is farther from the recognisers' consensus than the original. DANCER shows this mainly protects non-entity text.
- **Loanword and English-name failure mode** (Generative Annotation): phonetic text matching fails when recognisers transliterate an English name into Devanagari oddly, which is common in Hinglish. An audio-side check (the gpt-transcribe re-run, or TTS-based matching) is the remedy that worked there.

### Gaps
- No 2022–2026 paper found that directly compares **pinyin with tones vs without tones vs initials/finals** for retrieval. JSPG uses tone-numbered pinyin but does not ablate tones.
- "PERT" and Chinese spelling-correction "confusion sets" (PLOME-style) for ASR were not located in this pass. No evidence was found on fuzzy-pinyin rules (平翘舌 zh/z, 前后鼻音 in/ing) used for retrieval.
- DANCER's Figure 1 (recall vs list size) values were not extractable.

---

## 4. Japanese: kana/kanji normalisation, reading-based (yomi) matching for names, user dictionaries with readings, reading-aware biasing

### Takeaway
Japanese has the same problem as Hindi name spellings: one pronunciation, many written forms (enharmonic kanji names). The approaches that worked match at the **reading (phoneme/kana) level** with a tuned similarity threshold, then map back to the canonical written form. Production dictionaries (AmiVoice) store `written + reading` pairs. Biasing strength swings keyword F1 widely and increases insertions.

### Cited Findings
- **Sudo et al. (Honda Research Institute Japan + Tokyo Tech; Interspeech 2023 [peer-reviewed]):** a retraining-free fix for "enharmonic" personal names (same reading, different kanji).
  - Method: a named-entity-aware ASR emits the name's **phoneme sequence**, which is compared with each dictionary entry using **Gestalt pattern matching, r = 2K / (|a| + |b|)** (the Ratcliff/Obershelp ratio, as in Python `difflib.SequenceMatcher.ratio`). The best-scoring entry replaces the name only if r > V_th.
  - Threshold sweep, CER-NE on the in-house set:

    | V_th | CER-NE |
    |---|---|
    | 0.0 (always replace) | 27.6 |
    | 0.5 (best) | 19.8 |
    | 0.8 | 22.2 |
    | 1.0 (exact match only) | 28.6 |

  - Main result: average CER-NE 35.0 → 22.5, a 35.7% relative reduction.
  - With a dictionary of 1,000 personal names, CER-NE was still better than with no dictionary (46.5% at I = 0). It was best when the dictionary held exactly the 33 test names.
  - Only 5.7% of utterances contained names, so the extra compute applied to few calls, [Sudo et al. 2023](https://www.isca-archive.org/interspeech_2023/sudo23b_interspeech.pdf)
- **Mitsubishi Electric / MERL (IPSJ SIG technical report 2024, non-archival):** enrolling keywords in **katakana or hiragana reading form** instead of kanji, then converting them back in post-processing.
  - It only worked after fine-tuning the model with 5% of training words randomly replaced by kana.
  - Bias weight β swung KW-F1 from 0.286 to 0.840 and CER from 13.2% to 40.2%.
  - Keyword **insertions (false alarms) rose from 1.6% to 6.8–12.0%** with biasing, while correct keywords rose from 36.1% to 72.1–89.1%.
  - **Choosing the enrolment orthography per keyword** (original vs kana, whichever scored better) beat always using kana: +0.12 KW-F1 and −0.4 CER points (katakana), +0.09 KW-F1 and −0.7 points (hiragana).
  - Gains held for keywords of ≥5 morae; short (~3-mora) words remain unsolved, [MERL TR2024-073](https://merl.com/publications/docs/TR2024-073.pdf)
- **AmiVoice API (Advanced Media) [vendor doc]:**
  - Per-request `profileWords` lasts only for that session. On the Hybrid engine the format is `written spoken` pairs separated by `|`, e.g. `"AMI あみ|AOI あおい"`, with hiragana readings in the examples.
  - On the End-to-End engine it becomes `written alternative-written-or-biasing-level`, e.g. `"AmiVoice アミボイス 0.8"`, i.e. keyword biasing with a strength rather than a reading, [AmiVoice request-based dictionary](https://docs.amivoice.com/en/amivoice-api/manual/user-dictionary-request-based)
  - Persistent profiles are stored via the `profilewords` API. If `profileId` and `profileWords` are both given, `profileWords` wins. Up to 5 user dictionaries per request [snippet-only], [AmiVoice user dictionary API](https://docs.amivoice.com/en/amivoice-api/manual/user-dictionary-api)
- **Hitachi (arXiv 2505.17410) [preprint; a different Hitachi paper from the "selective retrieval" work already covered]:** a Japanese/English rare-word corrector fed N-best text plus a 1-best phonetic rendering.
  - An **LLM-generated "simplified kana-like pronunciation"** (LSP) was the best notation: with ChatGPT, CSJ eval1 CER 15.5 → 13.7 and rare-word recall 44.5 → 82.0.
  - **IPA hurt badly** (CER 27.3, precision 91.9) through over-correction. Romanised kana from pyopenjtalk was in between.
  - The authors say LSP "helped prevent over-correction caused by an excessive focus on semantic aspects", [Hitachi LSP](https://arxiv.org/html/2505.17410v1)
- **Ko et al. (NAIST, NICT, NVIDIA, Kyoto) [preprint, arXiv 2408.16180]:** multi-pass augmented generative error correction (GER) over Japanese ASR.
  - Combining hypotheses from **several ASR systems**, several LLM correctors and ROVER cut SPREDS-U1-ja CER from 12.91 (Whisper-v3) to 7.07.
  - On low-CER CSJ, single-system LLM GER was ineffective or harmful; e.g., Qwen on Eval3 reached 18.8% vs a ~3% baseline.
  - CER scoring normalised full-width to half-width characters and removed punctuation, with no kana/kanji normalisation, [Ko et al.](https://arxiv.org/html/2408.16180v2)
- IBM Japan's EMNLP 2024 Industry paper fine-tunes Japanese LLM correctors with "conservative data filtering" to curb over-correction. Its examples show hiragana/phoneme forms alongside the text [snippet-only], [Udagawa et al.](https://arxiv.org/html/2407.13300v2)
- **Azure:** ja-JP supports display-text formatting, and custom rules can map a spoken form to a written form using `{spoken>written}` notation [snippet-only]. Nothing confirmed that phrase lists accept separate readings, [Azure display text format](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-custom-speech-display-text-format)
- **Google Cloud STT (language-agnostic):** boost must be >0, with a practical maximum of 20. Higher boost reduces false negatives but raises false positives (words appearing that were never spoken). Boost on a multi-word phrase applies to the whole phrase only, and the docs suggest adding bigrams if needed [snippet-only], [Google STT boost](https://docs.cloud.google.com/speech-to-text/docs/boost)

### Inferences
- **The "enharmonic name" problem is Parakh's spelling-variant problem** (Pooja/Puja, Laxmi/Lakshmi, Mohd/Mohammad). Sudo's recipe transfers almost exactly:
  1. Compute a reading key for the disputed span and for each context name.
  2. Score them with `difflib` ratio or normalised edit distance.
  3. Replace only above a tuned threshold.
  4. Write the **canonical spelling from the context list**, not the recogniser's spelling.

  Sudo found the best threshold at a middle value (0.5); both always-replace and exact-only were much worse. **Tune the threshold on held-out data rather than using exact or very loose matching.**
- **Per-name choice of hint orthography** (MERL): for each name, decide whether gpt-transcribe gets the hint in Devanagari, in Latin script, or both. The rival-spellings idea already does part of this. MERL shows that choosing per name beats one global script choice.
- **Short names are the false-alarm zone.** MERL's gains needed ≥5 morae, and CLOVA refuses to boost 1-syllable words (Q5). Parakh should apply a stricter acceptance rule to 1–2 syllable names (e.g., Om, Raj, Ali).
- **Feeding a pronunciation rendering to an LLM corrector** helps only if it is simple and native-script-like (LSP); IPA caused over-correction. If Parakh ever uses an LLM to arbitrate, give it a simple romanised pronunciation of the disputed span, not IPA.
- **Multi-system fusion works; single-system LLM correction is risky at low error rates** (Ko et al.). This backs Parakh's fusion-first design and its rule of writing a name only when the audio backs it.

### Gaps
- No primary-source evidence found on how Google or Azure handle Japanese phrase hints with readings, or how Whisper-based Japanese pipelines handle name prompts.
- The Sony/CMU phoneme-aware TCPGen result on CSJ was seen in a snippet only. It reportedly beat grapheme-only prefix-tree biasing, but the paper was not opened and the numbers are unverified.
- No production Japanese vendor publishes false-alarm rates for user dictionaries.

---

## 5. Korean: jamo-level matching, spacing normalisation, production contextual biasing (Naver CLOVA, Samsung, Kakao)

### Takeaway
The richest Korean production evidence is Naver CLOVA Speech's `boostings` spec. It enforces a minimum length (no 1-syllable boosts), recommends ≤500 keywords because similar keywords confuse each other, matches regardless of spacing, tolerates trailing particles (조사) only when the full keyword is present, and supports an `output|pronunciation` mapping. No 2022–2026 jamo-level contextual-biasing paper was found.

### Cited Findings
- **Naver CLOVA Speech `boostings` [vendor doc]:**
  - Format: `words` (comma-joined) with a `weight` of 1–5 (decimals allowed). For different weights per keyword, split them into separate entries. If a keyword is entered twice, the last weight wins.
  - Size: "최대 1,000개까지 입력 가능", with **≤500 recommended**, because more keywords slow processing and **increase confusion between similar keywords**. Korean and English only.
  - **`output|pronunciation`** format: `신라|실라` outputs "신라" when "실라" is spoken.
  - **1-syllable words are not boostable** because of misrecognition risk (e.g., 네, 응, no). 2+-syllable words can affect recognition of other words and should be dropped if they cause misrecognitions.
  - **Spacing-insensitive:** register only one of "클로바스피치" / "클로바 스피치".
  - **Particles:** `홍길동` applies to "홍길동님" and "홍길동이" but not "길동님". It applies only when the whole keyword is recognised.
  - A separate `forbiddens` list suppresses words; it needs exact spacing and case, [CLOVA Speech API](https://api.ncloud-docs.com/docs/ai-application-service-clovaspeech-longsentence)
- **Samsung (SLT 2022 poster; page returned 404, snippet-only):** on-device Korean NE correction replaces a misrecognised word with the nearest candidate from an on-device list (e.g., contacts), with a 6-gram on-device LM and 5.6% WER on a Korean test set. The matching method is unverified, [Samsung SLT 2022 poster](https://chenehk.github.io/assets/SLT2022_poster.pdf)
- **Korean jamo-level similarity (2023, Journal of Intelligence and Information Systems) [snippet-only; PDF unreachable]:** decomposes syllables to compute word similarity for finding new ASR errors and neologisms. Among decompositions, **initial-consonant (초성) extraction** reportedly performed best, [koreascience 2023](https://koreascience.kr/article/JAKO202328958555680.pdf)
- Older Korean work, before the 2022 window [snippet-only]: proper-noun ASR post-processing using phoneme variation plus a modified edit distance (Sogang University/SKT, 2014), [koreascience 2014](https://www.koreascience.kr/article/CFKO201408355727254.pdf)
- Kakao: no contextual-biasing paper or doc found.

### Inferences
CLOVA's rules translate directly to Hindi/Hinglish post-hoc acceptance:
- **Minimum-length gate:** do not accept hint-driven names of one syllable, and be strict with two.
- **Particle and postposition tolerance with a full-match requirement:** strip trailing *-ji, ne, ko, se, ka/ki/ke, wala* before matching, but require the full name stem, so that "Rahul ne" matches Rahul and "-hul" does not.
- **Spacing normalisation:** match "Ram Prasad" = "Ramprasad" = "Ram-Prasad" before comparing.
- **`output|pronunciation` mapping:** store each context name with both its canonical written form and one or more spoken renderings, and always write the canonical form.
- **Cap the list:** CLOVA explicitly says similar keywords confuse each other as the list grows. This is the same distractor effect seen in Chinese work and in Huber & Waibel.

Jamo decomposition is the Korean counterpart of splitting Devanagari into consonant and vowel-sign components. The reported 초성 (initial-consonant) result hints that a consonant-skeleton key may be a robust first-pass retrieval key for Indic names, with vowels used only for re-ranking. This is unverified and should be treated as a hypothesis to test.

### Gaps
- No 2022–2026 peer-reviewed Korean contextual-biasing paper using jamo units was found. Samsung and Kakao production numbers are unavailable.
- CLOVA publishes no false-alarm or recall figures for boostings.

---

## 6. Techniques for estimating whether a hotword was really spoken (confidence on boosted words, two-pass verification, rescoring with and without context)

### Takeaway
The CJK systems that limit false triggers do so in four ways:
1. An explicit "use none" outcome (SeACo).
2. An agreement test against the unbiased N-best (DANCER rejection).
3. A tuned phonetic-similarity threshold (Sudo).
4. Acoustic verification of each candidate against an **unbiased** model's frame posteriors before prompting (VISH; two-stage PSC/SOC filtering).

VISH is notable because it is plug-and-play with black-box downstream recognisers, using a frozen external CTC model as the verifier.

### Cited Findings
- **VISH / M-VISH / Bi-MVISH (SJTU X-LANCE + Nanjing University) [preprint, arXiv 2610.27867, 20 Oct 2026]:**
  - It is a training-free hotword pre-selector. It runs a constrained CTC Viterbi alignment for each candidate over frame-level posteriors, normalised by the number of aligned non-blank frames, from a **frozen external CTC model (SenseVoice-Small, 234M)** or the native encoder. It "returns a compact prompt subset without downstream-model modification or decoder access", and the paper notes WFST and lattice methods are "less convenient for black-box contextual ASR."
  - Frames where the blank posterior exceeds 0.997 are removed. A shared-prefix trie keeps the top Kp = 40 prefixes. A backward pass averaged with the forward pass helps names with a **weak onset** (e.g., "smolny").
  - Pre-selection Best-F1: M-VISH gains +0.9 to +11.7 absolute over the reproduced GLCLAP baseline (STOP2: 81.2 → 92.9 for M-VISH, 93.8 for Bi-MVISH). AISHELL-1-NE: 96.6 → 97.5 (M-VISH) and 97.6 (Bi-MVISH).
  - Downstream, the Top-10 hotwords go into the prompt "Transcribe speech to text. Some hotwords might help. The hotwords are {}".

    | Downstream setting | Metric | No bias | Oracle hotwords | Bi-MVISH | GLCLAP |
    |---|---|---|---|---|---|
    | Whisper-medium, AISHELL-1-NE | CER/B-CER | 7.3/21.3 | 4.3/7.4 | 4.4/7.6 | 4.6/9.1 |
    | Whisper-medium, LibriSpeech-other, 2k list | B-WER | 29.9 |, | 17.3 | 18.2 |
    | Prompt-SLAM-ASR, LibriSpeech-clean, 2k list | WER/B-WER |, |, | 1.4/3.7 |, |

    The CTC-Assistant result for Whisper-medium on AISHELL-1-NE was 4.7/9.9.
  - Latency at 2,000 candidates: 203 ms (M-VISH) vs 817 ms (CTC-Assistant).
  - The paper notes "large candidate lists weaken prompt conditioning, increase interference, and cause bias-driven substitutions in both hotwords and background words", citing BR-ASR. It also notes that unusual pronunciations or spelling variants may weaken the score, [VISH](https://arxiv.org/abs/2610.27867)
- **Two-stage contextual word filtering (Interspeech 2023):** an order-free posterior-sum confidence, then a sequence-order confidence, prune the list before biasing. Two stages beat one. Reported CER cuts: about 20% (music, large list) and about 40% (contacts), [Yang et al.](https://arxiv.org/abs/2301.06735)
- **SeACo "#" no-bias token:** the biasing path can abstain per output step, and the ASR distribution is then used unchanged, [SeACo-Paraformer](https://arxiv.org/html/2308.03266v4)
- **DANCER N-best rejection:** reject a correction whose pinyin distance to the beam-weighted N-best exceeds the original's. Without it, non-entity CER rises 4.00 → 4.64, [DANCER](https://arxiv.org/abs/2403.17645)
- **Sudo threshold:** phonetic-similarity gating with V_th = 0.5 was best; "always replace" (0.0) and "exact only" (1.0) were both much worse, [Sudo et al.](https://www.isca-archive.org/interspeech_2023/sudo23b_interspeech.pdf)
- **Generative Annotation NEC:** a speech-segment classifier keeps candidates with probability >0.3, at most 5. The corrector can output "<empty>" to decline, [Generative Annotation NEC](https://arxiv.org/html/2508.20700v2)
- **PARCO:** "hierarchical entity filtering" (phoneme-level retrieval plus confidence gating) lowered NE-CER from 4.07 to 3.56 at 5,000 distractors, [PARCO](https://arxiv.org/html/2509.04357v1)
- **Vendor guidance:**
  - Alibaba: compare the same audio with and without hotwords or context; high weights cause similar-sounding words to be replaced, [Alibaba](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)
  - Tencent: too many super-hotwords lower overall accuracy [snippet-only], [Tencent](https://cloud.tencent.com/document/api/1093/41111)
  - MERL: biasing raised keyword insertions from 1.6% to up to 12.0%, [MERL](https://merl.com/publications/docs/TR2024-073.pdf)
- **Evaluation practice:** CJK papers routinely report entity error (NE-CER, B-CER, K-CER) **and** non-entity error (NNE-CER, U-CER) separately to expose over-correction, [DANCER](https://arxiv.org/abs/2403.17645); [JSPG](https://arxiv.org/html/2605.16896v1); [RASTAR](https://arxiv.org/abs/2602.12287)
- Non-CJK but relevant: Huang & Wang (ASRU 2025) train a biasing decoder that scores each phrase's likelihood of being in the audio, filtering most candidates before shallow fusion. LibriSpeech only; no numbers on the abstract page, [Huang & Wang](https://arxiv.org/abs/2510.23849)

### Inferences
- **The closest published analogue to Parakh's cross-examination is VISH**: verify each candidate against an *unbiased* acoustic model, then prompt the downstream black-box recogniser with only a compact subset. Parakh's equivalent is the no-hint transcripts from Saaras and gpt-transcribe.
  - If running one small local model is acceptable alongside the APIs, a frozen open Indic CTC model could provide VISH-style length-normalised posterior scores per candidate name. This is a hypothesis; no Hindi result exists.
  - VISH's bidirectional trick suggests also scoring how well the end of a name matches. Hindi names often have weak onsets in phone audio.
- **A with-vs-without-context A/B is vendor-endorsed** (Alibaba), and DANCER's rejection rule formalises it: the hinted name must agree with the unbiased recognisers better than the original span does.
- **Watch collateral damage:** VISH and BR-ASR both report bias-driven substitutions in *background* words. Parakh should verify that the hinted re-run changes only the disputed span, and reject the hint result if other words shift. It should also report non-name WER alongside "names right" to show the +9.3 points did not cost non-name accuracy.

#### Consolidated copy list for Parakh (API-only), ranked by strength of evidence
1. **Shortlist hard before hinting:** 1–5 hints per span for prompt-style recognisers. Evidence: H-PRM (Qwen2-Audio best at top-1, MER 3.24 → 29.42 at top-50), RASTAR k = 3, VISH Top-10, SeACo ASF k = 50 (for a trained bias decoder, not prompting).
2. **Always keep a "none" option:** the no-hint transcript stays in the vote (SeACo "#" token, Generative Annotation "<empty>").
3. **N-best agreement rejection:** accept only if the proposed name's phonetic distance to the three recognisers' spans, weighted by reliability, is lower than the original span's (DANCER).
4. **Tuned similarity threshold on a reading key,** set at a middle value tuned on held-out data, then **write the canonical context-list spelling** (Sudo: 0.5 best; 0 and 1 both bad; AmiVoice/CLOVA written+reading pairs).
5. **Full-match-or-cancel:** a prefix-only or neighbour-swallowing match reverts to the no-hint transcript (Aho-Corasick fail-arc cancellation in sherpa-onnx, WeNet and icefall; CLOVA's whole-keyword rule).
6. **Stricter rules for short names and names that are common words** (CLOVA's no-1-syllable rule; MERL's ≥5-mora finding; Alibaba's weight 1–2 for common-sounding terms).
7. **Normalise spacing and strip postpositions/honorifics before matching** (CLOVA's spacing-insensitivity and particle handling).
8. **Use a second, non-phonetic signal for homophone ties** (DANCER descriptions, JSPG semantic and glyph cues). Pure phonetic retrieval increased NE-CER from 15.58 to 20.88 on homophone-heavy data.
9. **Order-free then order-aware retrieval:** bag-of-phonemes prefilter, then local alignment over all recognisers' outputs, taking the max (Two-stage PSC/SOC; JSPG Smith-Waterman over N-best).
10. **Per-name hint script choice** (Devanagari vs Latin vs both), learned from data rather than fixed globally (MERL: per-keyword orthography choice +0.09 to +0.12 KW-F1).

### Gaps
- No CJK paper was found that tests **shuffling hint order and voting** for prompt-based recognisers, so Parakh's order-shuffle voting has no direct CJK precedent or counter-evidence.
- No CJK study reports calibrated **confidence scores for boosted words** from commercial APIs. Vendors expose weights, not post-hoc confidence on hotword hits.
- VISH is a fresh preprint (Oct 2026). Its Mandarin evaluation is only AISHELL-1-NE with Whisper-medium, and the Speech-LLM backbone was English-only.
