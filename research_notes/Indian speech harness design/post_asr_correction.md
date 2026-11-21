# Training-free LLM post-ASR correction, multi-hypothesis selection/fusion, and retrieval-augmented named-entity correction

Scope: methods usable with only black-box ASR APIs plus prompted commercial LLMs and deterministic code. Research date 2026-11-21. Status labels: **[peer-reviewed]** = in ACL Anthology / ISCA archive; **[preprint]** = arXiv only, as of retrieval.

Note on how numbers were obtained: tables for the Hindi EACL 2026 paper and DiP-ASR (EMNLP Findings 2024) were read directly from PDF text. Numbers for the arXiv papers were pulled from the arXiv HTML full text by an automated page-reading tool. They were not re-checked by hand against the PDFs, so spot-check before quoting. Relative gains marked "(computed)" are my arithmetic from the reported table values, not the authors' figures. Items marked "(search snippet only)" were not opened.

---

## Q1. Which training-free methods report the largest gains (setup, data, baseline, metric, gain, training needed)?

### Takeaway
The strongest training-free entity results come from **constrained, closed-vocabulary entity edits over multiple hypotheses**. RECOVER uses GPT-4o with LLM-Select over 5 hypotheses plus entity-only edits drawn from a supplied entity list. It cuts entity-WER by 12-49% relative while keeping overall WER roughly flat, and reaches 53% relative E-WER reduction when fusing 5 commercial ASR vendors. DeRAGEC uses GPT-4o-mini, retrieves named-entity (NE) candidates, then filters them with a multiple-choice step. It cuts WER by 19-35% relative on CommonVoice/STOP. Free-form zero-shot rewriting gives small or negative gains and is model- and domain-dependent. Several of the named methods are **not** training-free: the Apple retrieval-augmented NEC (2409.06062), Generative-Annotation NEC, A-STAR/RASTAR, and Prakash et al. (Interspeech 2025) all fine-tune. Their retrieval and output-format ideas still transfer.

### Cited Findings

**RECOVER (Kumar & Sachdeva, Observe.AI India; arXiv 2603.16411 v2) [preprint], training-free**
- Setup: Whisper-large-v3 (and Whisper-small) decoded at temperatures {0, 0.2, 0.4, 0.6, 0.8} gives 5 hypotheses per segment. GPT-4o is the main corrector; GPT-4o-mini, Llama-3.3-70B and Mixtral-8x22B were also run. The datasets are Earnings-21 (1,013 entities), ATCO2 (446 callsigns), Eka-Medical (6,198 entities), Common Voice 22 English (3,098 entities) and ContextASR-Bench (3,704 movie names). Strategies compared: 1-Best, Entity-Aware Select (most exact entity-list matches), ROVER (Needleman-Wunsch alignment plus majority vote, insertions need 3 of 5 votes), LLM-Select (the LLM sees all 5 hypotheses plus top-K candidates, picks a base, and proposes entity-only edits), and Adaptive Routing. No model training; retrieval weights were swept on Earnings-21, [RECOVER](https://arxiv.org/html/2603.16411)
- GPT-4o LLM-Select vs. raw Whisper-large-v3, WER / E-WER (relative E-WER reduction):
  - Earnings-21: 12.34/15.88 → 12.39/9.76 (38.5%)
  - ATCO2: 35.80/41.95 → 33.70/34.63 (17.5%)
  - Eka-Medical: 12.96/15.59 → 9.79/11.94 (23.4%)
  - Common Voice: 9.96/17.94 → 9.79/9.16 (48.9%)
  - ContextASR: 7.17/3.19 → 7.07/2.78 (12.8%)
 , [RECOVER](https://arxiv.org/html/2603.16411)
- Entity recall gains with LLM-Select were +8.4, +10.0, +5.1, +14.1 and +0.5 pp. Precision fell slightly, e.g. Common Voice P 97.63 → 91.71 while R rose 70.08 → 84.21, [RECOVER](https://arxiv.org/html/2603.16411)
- Multi-vendor fusion on Earnings-21 used one hypothesis each from Whisper-large-v3, Speechmatics, Deepgram, AssemblyAI and AWS Transcribe.
  - Single vendors (WER/E-WER): Speechmatics 10.07/16.47, Deepgram 14.70/13.93, AssemblyAI 11.68/13.73, AWS 9.11/22.97.
  - Fused: GPT-4o LLM-Select 11.56/7.96 (49.9%); GPT-4o + ROVER 9.24/7.44 (53.2%); GPT-4o-mini 11.54/9.38 (40.9%).
  - Relative reductions are against the Whisper-large-v3 baseline of 15.88 E-WER, [RECOVER](https://arxiv.org/html/2603.16411)
- GPT-4o-mini is much weaker as the corrector: RWERR (relative E-WER reduction) of 28.2% on Earnings-21 and only 1.57% on ATCO2, vs. 38.5% and 17.5% for GPT-4o. Cost per 1,000 segments was USD 13.57 for GPT-4o (about 2.11 calls and ~4.4k tokens per segment) and USD 0.84 for GPT-4o-mini, [RECOVER](https://arxiv.org/html/2603.16411)
- External single-pass baselines on Earnings-21 (GPT-4o-mini), WER / E-WER (RWERR):
  - Zero-shot correction: 12.84 / 14.09 (11.3%)
  - Few-shot: 12.65 / 14.05 (11.6%)
  - N-best generative: 13.10 / 13.82 (13.0%)
  - N-best selection: 12.54 / 15.82 (0.4%)
  - N-best + entity list: 12.82 / 10.97 (30.9%)
  - Direct prompt + entity list: 12.55 / 10.60 (33.2%)
  - RECOVER LLM-Select: 12.48 / 11.40 (28.2%)
 , [RECOVER](https://arxiv.org/html/2603.16411)
- Sensitivity to the entity list (RWERR): 100% coverage 28.2, 75% 23.0, 50% 16.0, 25% 8.1. Adding 769 distractors to the 100% list gave 25.8. Retrieval budget: K=50 27.0, K=100 27.5, K=200 27.8 (best), K=400 26.7, full list 26.3, [RECOVER](https://arxiv.org/html/2603.16411)

**DeRAGEC (Im, Lee et al., POSTECH; arXiv 2506.07510) [preprint; venue not stated on page], training-free (in-context learning only)**
- Setup: Whisper-large-v3-turbo produces 5-best lists. GLiNER extracts NEs from the top hypothesis. The top-10 phonetically similar NEs are retrieved from a 3.0M-entity database (Epitran G2P plus Panphon features). Each candidate gets a phonetic-similarity score and a one-line definition. A multiple-choice "denoising gate" picks one NE and writes a rationale. The corrector (Llama-3.1-70B or GPT-4o-mini) then gets the 5-best list plus the chosen NE and rationale. Up to 5 ICL examples carry rationales synthesized offline by o1. Code: github.com/solee0022/deragec, [DeRAGEC](https://arxiv.org/html/2506.07510)
- WER, GPT-4o-mini:
  - CommonVoice 7.7 (ASR) → 6.9 (5-best GEC) → 7.1 (RAGEC, all candidates) → 6.2 (DeRAGEC); oracle with the gold NE given is 6.0.
  - STOP 8.9 → 7.4 → 6.6 → 5.8; oracle 5.7.
  - Relative to raw ASR (computed): 19.5% CV, 34.8% STOP. The paper reports a 28% average.
  - NE hit ratio (GPT-4o-mini): CV 0.751 → 0.813, STOP 0.787 → 0.842.
 , [DeRAGEC](https://arxiv.org/html/2506.07510)
- Separating NE selection (the MCQ step) from correction matters: without the MCQ step WER is 6.8 and NE hit 0.780; with it, 6.0 and 0.831 (CV, Llama), [DeRAGEC](https://arxiv.org/html/2506.07510)

**LIR-ASR "Listening, Imagining & Refining" (Liu et al.; arXiv 2509.15095 v2) [preprint], training-free**
- Setup: Whisper-medium / Whisper-large-v3 on FLEURS test subsets (945 Chinese, 647 English utterances). Correctors are Qwen3-235B and DeepSeek-V3.1. The LLM generates phonetic "neighbor" variants via G2P and similar-sounding substitutions, scores them, and fuses them. Rule constraints filter candidates (phonetic consistency, length/structure), greedy acceptance keeps only non-worsening changes, and a finite-state machine controls search depth (at most 8 iterations, candidate pool 3), [LIR-ASR](https://arxiv.org/html/2509.15095)
- DeepSeek-V3.1 LIR-ASR vs. no correction, as tabulated: Whisper-medium ZH 5.14/10.21 → 3.20/5.91; Whisper-medium EN 1.92/4.49 → 1.68/3.70; Whisper-large-v3 ZH 3.98/7.50 → 2.89/5.23; Whisper-large-v3 EN 1.75/4.23 → 1.59/3.60. The abstract claims "up to 1.5 pp" average reduction, which does not obviously match the table deltas (+0.86/+2.00). Flagged as an internal inconsistency, [LIR-ASR](https://arxiv.org/html/2509.15095)

**"Can Generative LLMs Perform ASR Error Correction?" (Ma, Qian, Manakul, Gales, Knill; arXiv 2307.04172 v2, 2023) [preprint], training-free**
- Setup: ChatGPT (gpt-3.5-turbo-0613, not GPT-4) on 5-best lists from a Conformer-Transducer and Whisper small.en. Test sets: LibriSpeech test_other, TED-LIUM3, Artie Bias. Modes: zero-shot or 1-shot; unconstrained generation, "select" (choose an N-best member), and "closest" (map the LLM output to the nearest N-best hypothesis by Levenshtein distance), [Ma et al. 2023](https://arxiv.org/html/2307.04172v2)
- Best gains (Transducer):
  - TED 13.53 → 10.13 with 1-shot unconstrained (25.1%).
  - Artie 23.67 → 18.73 with 0-shot unconstrained (20.9%, computed).
  - LibriSpeech 6.90 → 6.24 with 1-shot closest (9.6%, computed).
  - Oracle 5-best WERs were 4.59 / 10.71 / 17.95.
 , [Ma et al. 2023](https://arxiv.org/html/2307.04172v2)
- Follow-up "ASR Error Correction using Large Language Models" (Ma, Qian, Gales, Knill; arXiv 2409.09554, submitted to IEEE). It adds N-best/lattice-constrained decoding for unseen domains and zero-shot ChatGPT correction. The EACL 2026 Hindi paper cites it as IEEE/ACM TASLP 2025. I did not retrieve its numbers, [Ma et al. 2024](https://arxiv.org/abs/2409.09554); venue per [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)

**ProGRes (Tur, Moumen, Ravanelli; arXiv 2409.00217 v2) [preprint; page does not state a venue], no fine-tuning (interpolation weight α tuned on validation data)**
- Setup: The LLM (GPT-3.5, GPT-4/GPT-4-Turbo, or Llama-3) is prompted with the n-best list and writes one extra hypothesis, giving n+1 candidates. All candidates are rescored with (1−α)·ASR score + α·Llama-3-8B log-likelihood. ASR1 is an ESPnet Conformer trained on SPGISpeech and tested on CommonVoice 14 (mismatched). ASR2 is a SpeechBrain WavLM-CTC trained and tested on CommonVoice 16.1, [ProGRes](https://arxiv.org/html/2409.00217v2)
- GPT-4 results:
  - ASR2: 12.38 → 9.39 prompt-only, 9.32 with ProGRes (24.7% relative, paper-reported).
  - ASR1 (mismatched, 42.94 baseline): 42.65 prompt-only, 40.84 ProGRes (~4.9%, computed).
  - The paper has internal inconsistencies: its table baseline row reads 43.75/13.97, and the text gives 9.82 vs. the table's 9.32 for GPT-4 ProGRes on ASR2.
 , [ProGRes](https://arxiv.org/html/2409.00217v2)

**Retrieval-augmented NE correction (Pusateri et al., Apple; arXiv 2409.06062) [preprint], requires LoRA fine-tuning**
- Setup: in-house CTC ASR; OpenLLaMA-7B with LoRA rank 4; a 2.6M-entity database; retrieval with Acoustic Neighbor Embeddings (vs. T5 and BM25). Entity spans are found by regex templates, all n-grams, or a trained NE tagger. Data: synthetic music queries and STOP, [Pusateri et al.](https://arxiv.org/html/2409.06062)
- WER, best system (template matching, top-1 hint): head 6.98 → 4.70 (32.6%), torso 7.68 → 4.97 (35.3%), tail 7.98 → 4.87 (39.0%), STOP 4.53 → 4.18 (7.7%). The paper reports overall WER only, no entity error rate. **In-context learning instead of LoRA gave "large WER regressions"** (no numbers; base 7B model), [Pusateri et al.](https://arxiv.org/html/2409.06062)
- Retrieval top-1 recall: acoustic embeddings 84-86% vs. T5 79-81% vs. BM25 54-60%. Phoneme embeddings add under 1 pp over orthographic ones, [Pusateri et al.](https://arxiv.org/html/2409.06062)

**Generative Annotation NEC (Luo et al., Huawei; arXiv 2508.20700 v2; code github.com/L6-NLP/Generative-Annotation-NEC) [preprint], requires training**
- Setup: Chinese. Entities are synthesized with TTS into a speech-keyed datastore, and a trained classifier retrieves candidates from audio (threshold 0.3, at most 5). A fine-tuned generator (~10k examples) takes "cand1|||cand2<EC>transcript" and outputs **only the erroneous span(s)**, which code then replaces, or "<empty>" to reject. 20% of training prompts are deliberate no-match cases, [Generative Annotation NEC](https://arxiv.org/html/2508.20700)
- On commercial engines (BuzzWord set):
  - iFlytek: NE CER 56.46 → 14.09, NE recall 19.18 → 81.71.
  - Amazon: NE CER 73.67 → 19.42, NE recall 9.84 → 80.02.
  - **Non-entity CER unchanged** (iFlytek 11.18 → 11.19; Amazon 24.40 → 24.40).
  - The PED-NEC baseline (phonetic edit distance) reached only 46.42 / 39.36 recall.
 , [Generative Annotation NEC](https://arxiv.org/html/2508.20700)

**A-STAR / RASTAR (An et al., Midea; arXiv 2602.12287) [preprint], requires DPO training**
- Setup: Mandarin AISHELL-1 Conformer ASR; a BERT NER model (trained); top-3 candidates by Pinyin edit distance from 16,168 entities; Qwen3 0.6B/8B trained with self-taught DPO and adaptive thinking, [A-STAR](https://arxiv.org/html/2602.12287)
- NE-CER vs. the DANCER baseline: AISHELL-1 7.57 → 6.21 (17.96%), Homophone set 11.33 → 7.43 (34.42%). The untrained "Qwen3-8B thinking" row already reaches 6.47 / 8.14 (computed: 14.5% / 28.2% vs. DANCER), so most of the gain is available without the DPO step. That row still uses the trained NER and the retrieval front-end, [A-STAR](https://arxiv.org/html/2602.12287)

**Multi-ASR fusion + LLM (Prakash et al., Uniphore; "Better Pseudo-labeling with Multi-ASR Fusion and Error Correction by SpeechLLM", Interspeech 2025) [peer-reviewed per ISCA archive listing; numbers from arXiv 2506.11089 v1], requires fine-tuning**
- Setup: outputs from Icefall Zipformer, NeMo Parakeet RNNT 1.1B and Whisper-large-v3, encoded as a confusion set, e.g. `all|<>|[] right two|<too>|[too] bye`. The correctors are Llama-3.2-1B (QLoRA) or Qwen2-Audio, both fine-tuned on ~27k samples. No zero-shot GPT baseline is reported, [Prakash et al. arXiv](https://arxiv.org/html/2506.11089v1); [ISCA archive](https://www.isca-archive.org/interspeech_2025/prakash25_interspeech.html)
- Textual LLM vs. word-level majority-vote ensemble: call-centre sets improve 1.1-19% relative (e.g. DefinedAI banking 13.85 → 11.67). LibriSpeech gets much worse (test-clean 2.22 → 2.96, −33%; test-other 4.06 → 5.21, −28%), [Prakash et al. arXiv](https://arxiv.org/html/2506.11089v1)

**RLLM-CF "Fewer Hallucinations, More Verification" (Fang et al.; arXiv 2505.24347 v3) [preprint], training-free**
- Setup: GPT-4o and DeepSeek-V2 on WeNet Conformer outputs (AISHELL-1/2, LibriSpeech). Three stages: (1) error pre-detection, where the sentence is kept if no error is found; (2) chain-of-thought subtasks (localize → pronunciation → candidates → select) with iteration; (3) answer verification, falling back to the original if the format or steps fail, [RLLM-CF](https://arxiv.org/html/2505.24347v3)
- GPT-4o: AISHELL-1 CER 5.17 → 4.06 (21%), AISHELL-2 5.57 → 4.95 (11%), LibriSpeech test-other 9.50 → 8.41 (11.4%), [RLLM-CF](https://arxiv.org/html/2505.24347v3)

**GEC-RAG (Robatian et al.; arXiv 2501.10734) [preprint] (search snippet only)**
- Treats the ASR as a black box. Builds a knowledge base of (ASR 1-best/5-best, ground truth) pairs and retrieves lexically similar past examples by TF-IDF as in-context examples. Target language is Persian. I did not retrieve its numbers, [GEC-RAG](https://arxiv.org/abs/2501.10734v1)
- DARAG "Failing Forward" (Ghosh et al., Findings of ACL 2025) [peer-reviewed] uses synthetic training data plus NE retrieval. It reports 8-30% relative WER improvement in-domain and 10-33% out-of-domain, but it is trained (search snippet only), [DARAG](https://aclanthology.org/2025.findings-acl.125)

### Inferences
- The training-free ranking for **entity accuracy** is roughly: (a) LLM-Select + closed-vocabulary entity edits over multiple hypotheses or vendors (RECOVER, up to ~50% E-WER cut); (b) retrieve-then-select-then-correct (DeRAGEC); (c) N-best generative correction without entity context, which gives ~10-13% E-WER cuts in RECOVER's baselines; (d) plain zero-shot rewrite, which is small and often negative.
- The single most important input is a **high-coverage entity list**. RECOVER's gain drops from 28% to 8% as coverage falls from 100% to 25%. For this harness, the user's contacts and places are exactly that list, which is the main structural advantage over raw Saaras and over gpt-transcribe with keywords.
- RECOVER's multi-vendor result (5 different commercial ASRs → 53% E-WER cut, and WER 9.24 that beats every single vendor except AWS's 9.11) is the closest published analogue to fusing gpt-4o-transcribe with Saaras v3. Vendor diversity seems to be worth more than temperature diversity from one model.
- Use a GPT-4o-class model (or better) for the edit/critic step. GPT-4o-mini lost most of RECOVER's gain on the noisy ATCO2 domain, and the Hindi zero-shot failures below are also with GPT-4o-mini.

### Gaps
- No paper evaluates any of these methods on gpt-4o-transcribe / gpt-transcribe or Sarvam Saaras outputs.
- GEC-RAG numbers and Ma et al. 2024/TASLP numbers were not retrieved. ProGRes's venue was not confirmed (some listings suggest ICASSP 2025, but the arXiv page does not say so).
- RECOVER's "1-Best" strategy also shows a ~39% E-WER cut on Earnings-21. That implies the entity-edit pipeline runs on top of every base-selection strategy, but the fetched text described 1-Best as "passed through unchanged". The exact pipeline composition should be checked in the PDF.
- Eka-Medical in RECOVER may be Indian-accented (Eka Care is an Indian company), but the paper excerpt did not state its language or accent.

---

## Q2. Failure modes (over-correction, hallucinated entities, large candidate lists, code-mixed/non-English) and training-free mitigations

### Takeaway
Unconstrained LLM correction reliably over-edits. It deletes disfluencies, "normalizes" rare names to common spellings, invents content, and in the worst reported case raised CER from 5.06 to 53.10. The damage is worse on strong ASR outputs, on Indic languages, and with smaller or weaker models. Mitigations that work without training:
- Restrict edits to entity spans.
- Require every replacement to come from a closed list.
- Keep candidate lists small or explicitly filtered.
- Add a no-change / empty option and a verification step that falls back to the original.
- Add phonetic and length guardrails.

### Cited Findings

**Over-correction / rewriting correct words**
- RECOVER measured tokens changed on Earnings-21 (GPT-4o-mini): direct prompt + entity list 5.85%, N-best + entity list 7.93%, RECOVER 0.21%. The free-form variants still reached similar or better E-WER (10.60-10.97 vs. 11.40) but with higher WER (12.55-12.82 vs. 12.48; baseline 12.34), [RECOVER](https://arxiv.org/html/2603.16411)
- RLLM-CF (DeepSeek-V2, AISHELL-1): a plain correction prompt raised CER from 5.06 to 53.10. The hallucination types catalogued were instruction violations, redundant output, continued writing, blank output, repetition, and grammar "correction". Even with the full framework, 1,568 sentences were modified: 383 erroneous sentences were fixed and **98 originally correct sentences were broken**. Ablation, CER: plain 53.10 → + pre-detection 8.19 → + CoT 7.05 → + iteration 4.89 → + verification 4.69, [RLLM-CF](https://arxiv.org/html/2505.24347v3)
- Ma et al. (ChatGPT) on Whisper outputs:
  - 0-shot unconstrained made LibriSpeech worse (7.37 → 7.71) and TED much worse (3.89 → 5.84, ~+50%, computed), mainly through deletions of disfluencies and "redundant" words.
  - 14 LibriSpeech outputs were truncated (~0.2% absolute WER); the 1-shot example fixed this.
  - Giving only the 1-best hypothesis made zero-shot correction worse than baseline on LibriSpeech (8.25 vs. 6.90).
 , [Ma et al. 2023](https://arxiv.org/html/2307.04172v2)
- ProGRes: Llama-3 prompt-only correction worsened the mismatched ASR1 (42.94 → 49.12). Early prompt versions produced hallucinations: unnecessary extensions, repeated sentences, and unrelated additions, [ProGRes](https://arxiv.org/html/2409.00217v2)
- LIR-ASR: Qwen3-235B direct prompting worsened Whisper-large-v3 English (1.75/4.23 → 2.30/4.94), and "evolutionary" prompting worsened Whisper-large-v3 Chinese (3.98/7.50 → 5.64/9.11). Removing the rule constraints from LIR-ASR raised Whisper-large-v3 ZH from 2.89/5.23 to 6.62/9.27, worse than no correction, [LIR-ASR](https://arxiv.org/html/2509.15095)
- OpenAI cookbook (archived recipe): a GPT-4 "spell-check" pass inserted a product name in place of an unrelated word. The recommended prompt with a name list worked qualitatively on one fictitious recording, with no metrics reported, [OpenAI Cookbook](https://developers.openai.com/cookbook/examples/whisper_correct_misspelling)

**Hallucinated or "popularized" entities (directly relevant to Indian names)**
- DiP-ASR reports that the LLM replaced a correctly transcribed rare name with a more common one: "Preethi" became "Preeti" even when the ASR output was right. More generally, non-popular cross-lingual proper nouns get substituted with more common ones, [DiP-ASR, EMNLP Findings 2024](https://aclanthology.org/2024.findings-emnlp.399/)
- DeRAGEC names an "LLM bias toward frequent words" that makes rare NEs hard to recover, [DeRAGEC](https://arxiv.org/html/2506.07510)

**Degradation with large or noisy candidate lists**
- DeRAGEC:
  - Feeding all top-10 retrieved NEs (RAGEC) made GPT-4o-mini *worse* than plain 5-best correction on CommonVoice (7.1 vs. 6.9).
  - Candidate precision falls from 0.137 at K=1 to 0.032 at K=15.
  - Static phonetic-similarity thresholds hurt: PS≥0.9 cut recall to 0.126 and raised WER to 7.2; PS≥0.6 recall 0.697, WER 6.5.
  - The LLM MCQ gate kept recall at 0.839 while raising precision to 0.139.
 , [DeRAGEC](https://arxiv.org/html/2506.07510)
- Pusateri et al.: with all n-grams as queries, moving from 1 to 5 hints per query raised WER (head 4.68 → 4.83); extra candidates "seem to confuse the model", so the best configuration keeps only the top match, [Pusateri et al.](https://arxiv.org/html/2409.06062)
- A-STAR picked k=3 because more candidates add irrelevant entities that interfere, [A-STAR](https://arxiv.org/html/2602.12287)
- RECOVER is the exception at larger K, because candidates are only a menu for a closed-vocabulary edit with a critic. K=200 was best (27.8%), K=400 26.7%, the full list 26.3%, and 769 distractors cost ~2.4 pp, [RECOVER](https://arxiv.org/html/2603.16411)

**Merge/voting failures**
- ROVER and Entity-Aware Select inflated WER on noisy ATCO2 (35.80 → 40.54 and 40.04) through insertions, while LLM-Select reduced it to 33.70, [RECOVER](https://arxiv.org/html/2603.16411)
- In Ma et al., ROVER over a single system's N-best performed worse than the ASR baseline, [Ma et al. 2023](https://arxiv.org/html/2307.04172v2)

**Code-mixed / non-English**
- Hindi (EACL 2026): GPT-4o-mini zero-shot correction increased WER on both ASRs: IndicWav2Vec 28.60 → 31.77 (+11%) and IndicConformer 18.02 → 25.14 (+39.5%, computed). The authors list three failure modes: over-correction grows with model scale ("edit beyond necessity", "hallucinated or stylistic substitutions"), ICL LLMs overshoot minimal corrections, and out-of-domain drift, [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)
- Mandarin-English code-switching: one paper reports that LLM correction did not improve SEAME unless given a ground-truth language hint (search snippet only), [Aligning Speech to Languages, arXiv 2403.05887](https://arxiv.org/pdf/2403.05887)

**Training-free mitigations with evidence**
- *Closed-vocabulary, entity-only edits.* RECOVER requires each replacement to be exactly one entity-list phrase, bans grammar/punctuation/casing rewrites, and adds a critic that accepts or rejects each edit. It also applies a guardrail similarity floor of 0.5. Guardrail rejections ranged from 410 to 6,865 per dataset and critic rejections from 34 to 632, [RECOVER](https://arxiv.org/html/2603.16411)
- *Pre-detection, no-change default, and verification fallback.* RLLM-CF ablation, from CER 53.10 down to 4.69 (see above), [RLLM-CF](https://arxiv.org/html/2505.24347v3)
- *Empty / reject output.* In Generative Annotation NEC, outputting "<empty>" when no candidate matches, and returning only spans rather than whole sentences, kept non-entity CER unchanged. That paper is trained, but the output contract can be copied in a prompt, [Generative Annotation NEC](https://arxiv.org/html/2508.20700)
- *Phonetic and length rule constraints plus greedy "accept only if not worse".* This was the largest single ablation effect in LIR-ASR, [LIR-ASR](https://arxiv.org/html/2509.15095)
- *Snap the output back to an N-best member* ("closest" mapping by Levenshtein distance). This bounded the losses on Whisper (LibriSpeech 7.15 vs. 7.71 unconstrained), [Ma et al. 2023](https://arxiv.org/html/2307.04172v2)
- *Keep the original hypotheses in the candidate pool and interpolate with ASR scores* (ProGRes). It filters out noisy LLM outputs, [ProGRes](https://arxiv.org/html/2409.00217v2)
- *Explicit candidate filtering before correction* (DeRAGEC's MCQ gate) rather than static thresholds, [DeRAGEC](https://arxiv.org/html/2506.07510)
- *Bounded edit distance for retrieval.* DiP-ASR matches NER-tagged words to dictionary entries by grapheme and phoneme edit distance ≤ 2, [DiP-ASR](https://aclanthology.org/2024.findings-emnlp.399/)

### Inferences
- For Indian personal names, a protective rule is: **if a hypothesis token already exactly matches a contact (after transliteration normalization), lock it**. That directly addresses the Preethi→Preeti failure. Only allow replacement *into* a contact-list form, never out of one.
- Number tokens need deterministic handling. Even fine-tuned Hindi correctors broke about as many numbers as they fixed (see Q4), and LLMs "normalize" numbers.
- Present a large candidate list (RECOVER-style, ~100-200 retrieved by phonetic similarity) only when the LLM's output is restricted to choosing from it, and add a critic or guardrail. If candidates are injected as free-text hints, keep them to about 1-3.

### Gaps
- No paper reports a standardized "correct-word corruption rate". The closest proxies are RECOVER's tokens-changed percentages, RLLM-CF's 383-fixed vs. 98-broken sentence counts, and the Hindi paper's CW→IW counts.
- No quantified hallucinated-entity rate for GPT-4o-class models on Indian names was found.
- Chain-of-Correction (arXiv 2504.01519) describes a "correction threshold" to trade off under-correction against over-rephrasing, and segment-wise correction to avoid hallucination on long inputs. I saw it via search snippet only, with no numbers, [Chain of Correction](https://arxiv.org/html/2504.01519v2)

---

## Q3. Is selection (pick one hypothesis) more reliable than generation or token voting?

### Takeaway
Pure selection is **safer but nearly useless for entities**: it bounds the downside but can't recover an entity that no hypothesis contains (RECOVER: N-best selection gives a 0.4% E-WER change). Unconstrained generation has more upside but also the worst failures. Token voting (ROVER) helps when hypotheses come from genuinely different recognisers and hurts on a single system's N-best or on very noisy audio. The best evidence-backed design is a hybrid: **select a base hypothesis, then apply constrained, closed-vocabulary span edits**, with a verifier and a fallback to the original.

### Cited Findings
- RECOVER: "N-best selection, which may re-rank but not edit, is essentially flat (0.4%)". "Selection-based LLM-Select keeps WER below baseline" (where "baseline" in that phrase refers to the comparison systems; Earnings-21 WER was actually 12.39 vs. 12.34). "Merge-based fusion (ROVER, Entity-Aware Select) reduces E-WER but inflates WER on the extremely noisy ATCO2 domain." With 5 independent vendors, GPT-4o + ROVER gave the best WER and E-WER (9.24 / 7.44), [RECOVER](https://arxiv.org/html/2603.16411)
- RECOVER: Adaptive Routing, where an LLM picks the strategy per segment, did not beat fixed LLM-Select except marginally on ATCO2, [RECOVER](https://arxiv.org/html/2603.16411)
- Ma et al. (ChatGPT, zero-shot):
  - Selection was more robust on Whisper. LibriSpeech: select 7.24, closest 7.15, unconstrained 7.71 (baseline 7.37). TED: select 4.19 vs. unconstrained 5.84 (baseline 3.89, so every LLM mode lost there).
  - Unconstrained had more upside on the Transducer. Artie: unconstrained 18.73 vs. select 21.88 (baseline 23.67).
  - With "closest" mapping, hypothesis 1 was chosen for 67% of utterances, and gains came mostly from hypothesis 2.
  - Whisper N-best lists were low-diversity: on average only 2.6-3.0 unique hypotheses out of 5, driven by punctuation/capitalization (ITN) and repetition differences.
 , [Ma et al. 2023](https://arxiv.org/html/2307.04172v2)
- ProGRes: "LLM Rescoring" alone (selection by LLM score) gave little benefit, and was worse than baseline for Llama-3/GPT-3.5 in the table. Adding one LLM-generated hypothesis to the pool and rescoring jointly with ASR scores was best in 87.5% of configurations, [ProGRes](https://arxiv.org/html/2409.00217v2)
- DeRAGEC: turning NE choice into an explicit multiple-choice selection before generation improved WER from 6.8 to 6.0 and NE hit from 0.780 to 0.831, [DeRAGEC](https://arxiv.org/html/2506.07510)
- Hindi EACL 2026: the authors state, citing others, that "LLM re-scoring of N-best lists often underperforms compared to using a single 1-best hypothesis". In a pilot, ByT5 with n=5 hypotheses got WER 45, far worse than 1-best training, [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)
- Prakash et al.: a fine-tuned text LLM over 3 ASR outputs beat word-level majority voting on call-centre audio (+1-19%) but lost badly on LibriSpeech (−28% to −46%), where one component (NeMo) was already near-perfect, [Prakash et al.](https://arxiv.org/html/2506.11089v1)

### Inferences
- With gpt-4o-transcribe and Saaras v3, the hypotheses come from different vendors, so they will be more diverse than temperature samples. That favours RECOVER-style LLM-Select over 2-4 vendor outputs, with ROVER-like voting only as a tie-breaker for non-entity tokens. Normalize punctuation, casing and script **before** comparing hypotheses (Ma et al.'s Whisper diversity issue).
- When one recogniser is already strong (e.g. clean English), fusion can make things worse (Prakash on LibriSpeech; Ma on Whisper TED). Gate fusion and correction on disagreement: if hypotheses agree after normalization and no entity-list near-miss is present, pass the text through untouched.

### Gaps
- No head-to-head comparison of selection vs. generation on code-mixed Hindi-English with GPT-4o-class models was found.

---

## Q4. Results on Hindi, Hinglish, or Indian-accented English

### Takeaway
The Indic evidence is sparse and mostly cautionary. The only peer-reviewed Hindi post-ASR study (IIT Bombay, EACL 2026) found GPT-4o-mini zero-shot correction *increased* Hindi WER (+11% to +40% relative). Five-shot retrieval-selected examples gave only a 5% gain on the weaker ASR and still hurt the stronger one. For cross-lingual Indian proper nouns, dictionary-augmented few-shot prompting of gpt-3.5 (DiP-ASR, EMNLP Findings 2024) cut WER by 8-41% relative (computed) on small 50-utterance sets, while zero-shot often made things worse. No Hinglish-specific LLM correction numbers for GPT-4-class models were found.

### Cited Findings
**Post-ASR Correction in Hindi (Kumar, Krishna, Ramakrishnan, Jyothi; IIT Bombay; EACL 2026 Short, pp. 636-645) [peer-reviewed]**, code github.com/cyfer0618/Post-ASR-Correction-in-Hindi
- Data: Lahaja test set (12.5 h of Hindi, 132 speakers, 83 districts; read, extempore and conversational). Raw ASR WER: IndicConformer 18.02, IndicWav2Vec 28.60, IndicWhisper 32.17, SeamlessM4T 52.63, [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)
- GPT-4o-mini ICL (raw → corrected WER):
  - Zero-shot: W2V 28.60 → 31.77; IC 18.02 → 25.14.
  - Random examples, 1/3/5-shot: W2V 30.95 / 29.84 / 29.27; IC 24.51 / 22.13 / 22.19.
  - Sentence-embedding-similar examples, 1/3/5-shot: W2V 29.22 / 28.18 / 27.14; IC 22.88 / 22.04 / 20.89.
  - Only W2V with 3-shot and 5-shot similar examples beats raw ASR; every IndicConformer setting is worse than raw.
 , [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)
- Zero-shot LLaMA scaling (1B → 3B → 8B → Nanda-10B → 70B) shows an "n-shaped" curve: mid-sized models degrade most, and even 70B does not match fine-tuned mT5, [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)
- Fine-tuned small models (not training-free, for reference): mT5-base 16.17 on IndicConformer (−10.3% vs. 18.02, computed); ByT5 23.36 on IndicWav2Vec (−18.3%, computed), [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)
- Error-type analysis of the fine-tuned mT5 (IW→CW fixed / CW→IW broken / unchanged):
  - English words in Hindi speech (code-mixing): 637 / 283 / 3180
  - English numbers: 7 / 17 / 131
  - Hindi numbers: 36 / 24 / 94
  - Under-represented characters: 2254 / 1129 / 3296
  - ByT5, English numbers: 19 / 22; English words: 730 / 456.
  - **Even fine-tuned correctors break nearly as many code-mixed numbers as they fix**, [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)
- Hindi error taxonomy: transliteration of English words (e.g. "tourist" → ṭyūresṭa), English numbers written phonetically ("one" → vāna), Hindi numbers distorted (taitālīsa), word segmentation (gaīhai), compound splits (ratha yātrā), and under-represented graphemes, [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)
- Latency per utterance: GPT-4o-mini 2.03 s vs. mT5-small 0.97 s, [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)

**DiP-ASR: dictionary-based prompting for cross-lingual proper nouns (Kumar, Ghosh, Ramakrishnan; Findings of EMNLP 2024, pp. 6821-6828) [peer-reviewed]**, code github.com/cyfer0618/DiP-ASR
- Setup: wav2vec2-XLSR fine-tuned on English CommonVoice (an English ASR hearing Indian proper nouns) produces 5-best lists. NER tags proper nouns, which are matched against a master dictionary by grapheme and phoneme (G2P) edit distance ≤ 2. The dictionary comes from IMDb, Spotify and Kaggle Bollywood songs, transliterated from native script to Roman with a ~97%-accurate transliterator. The LLM is gpt-3.5-turbo-0613. Each language has 100 test utterances (50 "simple", 50 "complex"), selected for low ASR confidence, [DiP-ASR](https://aclanthology.org/2024.findings-emnlp.399/)
- WER: baseline → 0-shot → few-shot (teacher-forced examples) + dictionary:
  - Hindi-simple 57.53 → 59.53 → 46.83
  - Hindi-complex 45.46 → 40.78 → 29.94
  - Tamil-simple 50.40 → 49.60 → 40.46
  - Tamil-complex 50.14 → 47.32 → 32.21
  - Telugu-simple 56.76 → 58.69 → 52.38
  - Telugu-complex 68.65 → 72.16 → 40.32
  - Relative gains (computed): 18.6%, 34.1%, 19.7%, 35.8%, 7.7%, 41.3%. The paper itself says "an improvement range from 7% to 30%", which does not match these computations; the baseline it used may differ.
 , [DiP-ASR](https://aclanthology.org/2024.findings-emnlp.399/)
- Zero-shot often returned hypothesis 1 unchanged and was worse than baseline on 3 of 6 sets. 2-shot averaged better than 8-shot (51.77 vs. 54.14 WER). Using the N-best list gave a 3.5% WER improvement, [DiP-ASR](https://aclanthology.org/2024.findings-emnlp.399/)

**Hinglish / code-mixed and Indian-accented English**
- CLEAR (ICNLSP 2025) evaluates GPT-4 and other LLMs for Hindi-English code-switched ASR, but it guides decoding rather than post-correcting. I saw it via search snippet only and did not verify numbers, [CLEAR, ICNLSP 2025](https://aclanthology.org/2025.icnlsp-1.33.pdf)
- Mandarin-English generative error correction (Chen et al., 2023) reports reduced mixed error rate using N-best + LLM, but it uses trained adapters and is not Hindi (search snippet only), [GER for code-switching](https://arxiv.org/html/2310.13013v1)

### Inferences
- Do **not** run a free-form "fix this Hindi/Hinglish transcript" pass. The only controlled Hindi evidence shows it raises WER, especially on the stronger recogniser (IndicConformer 18 → 25). Saaras v3 and gpt-4o-transcribe are presumably closer to the strong-recogniser case.
- What did help in Indic settings was (a) supplying an external dictionary of the target proper nouns with phonetic/grapheme matching (DiP-ASR) and (b) retrieval-selected few-shot examples (Hindi paper). Both are available training-free: contacts and places become the dictionary, and the user's past corrected utterances become GEC-RAG-style examples.
- Transliteration normalization (Devanagari ↔ Roman) has to be a first-class deterministic step. DiP-ASR built its dictionary that way, and Hindi errors are dominated by transliteration and segmentation.

### Gaps
- I found no published zero-shot GPT-4o / GPT-4.1 / GPT-5-class post-correction results on Hinglish or Indian-accented English phone speech. I also found no results on Sarvam or OpenAI transcribe outputs.
- DiP-ASR's test sets are tiny (50 utterances per condition) and use gpt-3.5. The Hindi paper's ICL is GPT-4o-mini only; the authors say GPT-4o was not tested "due to limited funds".

---

## Q5. Practical prompt designs reported to work with GPT-4-class models

### Takeaway
The prompts that work share these traits:
- They show numbered N-best hypotheses (or several vendors' outputs).
- They supply a small, explicit candidate set per suspicious span, with phonetic similarity attached.
- They restrict output to exact candidate strings or spans.
- They forbid stylistic edits.
- They ask for output only, in tags.
- They allow "no change".
- They use 1-3 well-chosen examples rather than many.
- They separate selecting the entity from rewriting the sentence, and verify the result afterwards.

### Cited Findings
- **RECOVER (propose → critic).** The proposer emits entity-only find/replace edits. Each replacement must be exactly one phrase from the entity list, with no grammar, punctuation or casing rewrites, and near-miss corrections are encouraged. The critic accepts or rejects each edit with a reason, and can flag a missed entity or request more candidates. Inputs are 5 hypotheses plus the top-K (~200) retrieved entity candidates. A deterministic guardrail rejects low-similarity replacements (similarity floor 0.5). Full prompt text is not published, [RECOVER](https://arxiv.org/html/2603.16411)
- **DeRAGEC (select, then correct).**
  - Module 2 is an MCQ: options formatted "[ID letter]: [Named-Entity] ([PS] | [Definition])"; the model reasons inside `<think>` and answers in `<answer>`.
  - Module 3 receives the 5-best list plus the selected NE and rationale, and must "return only the corrected transcription".
  - Up to 5 rationale-bearing few-shot examples.
 , [DeRAGEC](https://arxiv.org/html/2506.07510)
- **DiP-ASR prompt (quoted from the paper's Table 1).**
  - System: "You are an Automatic Speech Recognition error correction tool".
  - User: "Perform error correction on the top 5 output generated by an Automatic Speech Recognition (ASR) System. The ASR hypothese are : hypothesis 1: '…' … hypothesis 5: '…'".
  - Dictionary: "'dumda' can be ['dumda', 'jhumka', 'thumka', 'dum'] …", followed by "Please provide only one corrected ASR hypothesis for the given utterance (hypothesis) using Dictionary, do not add any extra word or explanations."
  - 2-shot was the chosen setting.
  - Note that the dictionary entry includes the original word as an allowed option.
 , [DiP-ASR](https://aclanthology.org/2024.findings-emnlp.399/)
- **Ma et al.** sort hypotheses by ASR posterior inside numbered hypothesis tags and ask for the corrected sentence with no explanation. For selection, the model returns `<option?>…</option?>`. A 1-shot example removed truncation errors. A post-hoc Levenshtein "closest" mapping to the N-best is applied in code, [Ma et al. 2023](https://arxiv.org/html/2307.04172v2)
- **ProGRes** prompt: "Perform error correction on the top outputs generated by an ASR system", with the answer enclosed in < > and no commentary. The original hypotheses stay in the pool for rescoring, [ProGRes](https://arxiv.org/html/2409.00217v2)
- **RLLM-CF** (GPT-4o; 3 few-shot examples):
  - Step 1: ask whether there is any error; if none, keep the sentence.
  - Step 2: localize the error → assess pronunciation → generate candidates → select.
  - Step 3: verify format and step completion, otherwise revert.
  - Settings: temperature 0.2, top-p 0.8.
 , [RLLM-CF](https://arxiv.org/html/2505.24347v3)
- **Hindi EACL 2026 prompt (Appendix H, quoted):** "You are given an ASR hypothesis of a spoken utterance. The hypothesis may contain misrecognized words, incorrect word segments, or code-switching mistakes. Your job is to produce the best possible corrected text… Please correct any errors in 1. Incorrect transliteration of English words 2. Incorrect transliteration of English numbers 3. Incorrect transcription of native Hindi numbers 4. Misrecognition of underrepresented characters 5. Splitting of compound words 6. Incorrect word segmentation… Output only the final corrected output (no extra commentary)". With GPT-4o-mini, this open-ended prompt **raised** WER zero-shot, [Kumar et al. EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)
- **Span-output contract (Generative Annotation NEC, trained but copyable).** Input "candidates joined by ||| <EC> transcript". The model outputs only the erroneous span(s) to replace, or "<empty>". Code performs the substitution, so non-entity text cannot drift, [Generative Annotation NEC](https://arxiv.org/html/2508.20700)
- **Hint format (Pusateri et al., trained).** Each retrieved entity is a hint tagged `[H]`, the transcript is tagged `[A]`, and `[P]` cues the prediction. One hint per query span worked best, [Pusateri et al.](https://arxiv.org/html/2409.06062)
- **OpenAI cookbook.** Whisper's `prompt` parameter (cited limit 244 tokens) fixed only some name misspellings. A GPT-4 post-processing system prompt ("Your task is to correct any spelling discrepancies in the transcribed text…", followed by the list of correct names, "only add necessary punctuation", "use only the context provided") fixed the spellings in the demo. No metrics; archived recipe, [OpenAI Cookbook](https://developers.openai.com/cookbook/examples/whisper_correct_misspelling)
- **Prakash et al. confusion-set encoding** for multi-ASR input: `all|<>|[] right two|<too>|[too] bye`, with low-confidence regions in brackets. The corrector was fine-tuned, [Prakash et al.](https://arxiv.org/html/2506.11089v1)

### Inferences
A prompt-and-code contract for the harness, synthesized from the above (not a single published recipe):
1. Input: 2-4 normalized vendor transcripts (gpt-4o-transcribe with keywords, Saaras v3, optional temperature variants), numbered.
2. For each suspicious span (found by disagreement, or by phonetic near-match to a contact or place), attach the top 1-5 candidates from the user's lists, with transliteration and phonetic-similarity scores. Always include "KEEP_AS_IS".
3. The LLM returns JSON: `{base_hypothesis_id, edits:[{span, replacement_id | "KEEP"}]}`. Nothing else.
4. Code applies the edits only if: the replacement is an exact list entry; the phonetic similarity is above a floor (RECOVER used 0.5); the token edit distance is within a cap (DiP-ASR used ≤2 for matching); and the span was not already an exact contact match.
5. An optional critic call (RECOVER) or verification step (RLLM-CF) can reject edits. Fall back to the base hypothesis.
6. Numbers, dates and currency go through deterministic normalizers, not the LLM.

Few-shot examples should be 1-3 and drawn from the user's own corrected history (GEC-RAG / Hindi-paper similarity selection). 2-shot beat 8-shot in DiP-ASR.

### Gaps
- Full prompt texts for RECOVER, LIR-ASR, A-STAR and RLLM-CF's few-shot examples are not published in the fetched versions. The repos (deragec, DiP-ASR, Post-ASR-Correction-in-Hindi, Generative-Annotation-NEC) may contain them but were not inspected.
- No study tested OpenAI structured outputs / JSON-schema-constrained correction. The JSON-edit contract above is an inference, not a reported result.
