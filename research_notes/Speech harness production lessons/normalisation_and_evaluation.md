# Normalisation, transliteration and evaluation practice in non-English production ASR (for Parakh)

Scope note: this file does not repeat earlier notes in `research_notes/Indian speech harness design/`. Those already cover misheard, indic-transliteration, IndicXlit, NeMo Hindi ITN basics, OI-WER/voi_oiwer, IndicContextEval NEER, MUCS 2021 T-WER, basic paired bootstrap, and the Gramvaani/MUCS/Kathbath/IndicVoices dataset table. Status labels: "preprint" means arXiv only; "vendor" means a self-published company source. Code marked "tested" was run on this Mac (Python 3.10.0, `unicodedata` Unicode 13.0).

## 1. Text normalisation / ITN for non-Latin languages, and the accepted way to normalise Devanagari before WER

### Takeaway
No production stack ships a ready-made "Devanagari pre-WER normaliser". Teams combine three things: Unicode NFC, a script-aware cleanup (indic-nlp-library's `DevanagariNormalizer` is the de facto one), and punctuation removal that must not touch combining marks. Whisper's `BasicTextNormalizer` breaks Hindi: it turns every matra and virama into a space. Any Parakh code path, or any third-party leaderboard number, that uses it is invalid for Devanagari. Vendors' ITN (digits and formatting) is on by default and not configurable for hi-IN, so Parakh must normalise numbers on *both* sides itself.

### Cited Findings
**Whisper normaliser pitfall**
- Whisper `basic.py` code:
  - `remove_symbols()` applies NFKC, then replaces every character whose Unicode category starts with M, S or P with a space (`unicodedata.category(c)[0] in "MSP"`).
  - `remove_symbols_and_diacritics()` applies NFKD, drops category `Mn`, and also spaces out M/S/P.
  - `BasicTextNormalizer.__call__` lowercases, deletes `[...]`/`<...>` and `(...)` spans, applies one of these two, and collapses whitespace.
  - [openai/whisper basic.py](https://raw.githubusercontent.com/openai/whisper/main/whisper/normalizers/basic.py)
- Reproduced locally (tested). Devanagari vowel signs are category Mn/Mc, so the default path gives:
  - "मेरा नाम राहुल है" → "म र न म र ह ल ह"
  - "पच्चीस हज़ार रुपये।" → "पच च स हज र र पय"
  - Both forms of "आँख आंख" → "आ ख आ ख"
  - Unicode categories checked locally: ि ा ः = Mc; े ् ं ँ ़ = Mn; । ॥ = Po; ZWNJ/ZWJ = Cf. Local check with Python 3.10 `unicodedata`.
- Manohar & Pillai, "What is lost in Normalization?" (arXiv 2409.02449 v4; ACL Anthology lists it as EMNLP 2024 main, 2024.emnlp-main.607; self-described position paper):
  - Mechanism: Whisper's normaliser removes matras and virama.
  - With whisper-small on FLEURS, Whisper normalisation cuts WER by 21.9 points for Hindi, 41.5 for Tamil and 152.2 for Malayalam. English drops 5.1 and Finnish 3.2.
  - METEOR similarity of normalised text to the original: Hindi 0.38, Tamil and Malayalam 0, English 0.97.
  - The normaliser was adopted for evaluation by MMS, Seamless and AssemblyAI Conformer-1, and it propagates through the Hugging Face Transformers Whisper normaliser.
  - The paper gives no concrete fix, only "language-specific normalization routines".
  - [arXiv html v4](https://arxiv.org/html/2409.02449v4); [ACL preview](https://preview.aclanthology.org/setup/2024.emnlp-main.607)
- The `whisper_normalizer` PyPI package (Kurian Benoy) adds an Indic normaliser adapted from indic-nlp-library because "using Whisper normalization can cause issues in Indic languages". I did not verify its matra handling., [PyPI](https://pypi.org/project/whisper-normalizer/); [docs](https://kurianbenoy.github.io/whisper_normalizer/1b.indic_normalizer.html)

**indic-nlp-library `DevanagariNormalizer` (MIT; the closest thing to a standard)**
- Constructor defaults: `remove_nuktas=False`, `nasals_mode='do_nothing'` (options `to_anusvaara_strict`, `to_anusvaara_relaxed`, `to_nasal_consonants`), `do_normalize_chandras=False`, `do_normalize_vowel_ending=False`., [indic_normalize.py](https://raw.githubusercontent.com/anoopkunchukuttan/indic_nlp_library/master/indicnlp/normalize/indic_normalize.py)
- Base steps, always on:
  - Removes BOM, U+FFFE, word joiner and soft hyphen.
  - Maps ZWSP and NBSP to a space, and deletes ZWNJ and ZWJ.
  - Maps fancy quotes and dashes to ASCII.
  - Optionally maps chandra forms: chandra-e/o → e/o, and chandrabindu → anusvara (offsets 0x00/0x01 → 0x02).
  - Optionally folds nasals. The strict mode turns a nasal+halant before a homorganic consonant into anusvara.
  - [same file](https://raw.githubusercontent.com/anoopkunchukuttan/indic_nlp_library/master/indicnlp/normalize/indic_normalize.py)
- Devanagari-specific steps:
  - Maps ॲ (U+0972) → ए.
  - Decomposes precomposed nukta letters (U+0929, U+0931, U+0934, U+0958–095F) into base + U+093C.
  - Optionally deletes the nukta.
  - Maps `|` → । (danda).
  - Turns ":" after a Devanagari letter into visarga.
  - It performs **no NFC/NFD step**; the module does not import `unicodedata`.
  - `IndicNormalizerFactory().get_normalizer('hi', ...)` returns it.
  - [same file](https://raw.githubusercontent.com/anoopkunchukuttan/indic_nlp_library/master/indicnlp/normalize/indic_normalize.py)
- NFC behaviour (tested locally):
  - NFC *decomposes* क़ (U+0958) and ड़ (U+095C) into base + nukta, because they are Unicode composition exclusions.
  - NFC leaves ऩ (U+0929) composed.
  - So NFC alone does not make all nukta letters uniform; the U+0929/0931/0934 cases need explicit decomposition.
  - Local test with Python `unicodedata` 13.0.
- Sarvam (vendor, Apr 2026) recommends three steps before evaluation:
  - "Apply Unicode NFC normalisation to all text before evaluation."
  - Strip whitespace.
  - Pick one canonical digit form (Arabic or Indic) for both sides.
  - It does not address nukta or anusvara.
  - [Sarvam blog](https://www.sarvam.ai/blogs/evaluating-indian-language-asr)
- Hindi spelling-variant metrics:
  - AWER/ACER (Shah et al., arXiv 2203.16601) target "half characters and multiple written forms of the same character" in Hindi.
  - They reported up to 3% (AWER) and 7% (ACER) "interpretability" gains.
  - The paper is **withdrawn by the authors**, so do not cite it as evidence.
  - [arXiv abs](https://arxiv.org/abs/2203.16601)
- The Factors-affecting-Indic-ASR study (preprint, Jun 2026) normalised both sides only "by removing punctuation, tags, special tokens, and other non-verbal artifacts". This typical research practice does no nukta or anusvara folding., [arXiv 2606.09335](https://arxiv.org/pdf/2606.09335)
- The Vistaar/IndicWhisper repo README does not document its eval normalisation; it exposes only `--do_normalize_eval="False"`., [GitHub AI4Bharat/vistaar](https://github.com/AI4Bharat/vistaar)

**ITN stacks**
- Google Sparrowhawk:
  - It is "an open-source implementation of Google's Kestrel" TTS text-normalisation system, with grammars written in Thrax (OpenFst).
  - Its tokenizer/classifier and verbaliser exchange data as protobufs.
  - The repo is described as archived/unmaintained.
  - [google/sparrowhawk README](https://github.com/google/sparrowhawk/blob/0d2fe1305439c213653ed15da639de9b72f454a4/documentation/README.md); [Khmer THA paper refs](https://arxiv.org/pdf/2609.30984)
- NVIDIA NeMo-text-processing:
  - The language matrix lists Hindi (hi), Chinese (zh), Japanese (ja) and Arabic (ar), each with two marks. The flattened table did not show which columns, presumably TN and ITN.
  - It also lists Marathi (one mark) and a Spanish-English `es_en` code-switched row. There is **no hi-en row**.
  - CLI: `python inverse_normalize.py --text="..." --language=en`.
  - [NeMo docs 25.09](https://docs.nvidia.com/nemo-framework/user-guide/25.09/nemotoolkit/nlp/text_normalization/wfst/wfst_text_normalization.html)
- NeMo install on macOS: "Pip installation on MacOS and Windows are not supported due to the dependency Pynini". Use `conda install -c conda-forge pynini=2.1.6.post1`; the examples use Python 3.10. Grammars export to FAR files for Sparrowhawk deployment., [GitHub NeMo-text-processing](https://github.com/NVIDIA/NeMo-text-processing); [NeMo ITN paper](https://arxiv.org/pdf/2104.05055)
- Amazon ITN research: Amazon's neural ITN paper covers cardinals, fractions, ordinals, years, floats, dates, times, currency and units, and was evaluated on English, Spanish, German and Italian, not Hindi., [arXiv 2102.06380](https://arxiv.org/pdf/2102.06380)

**Vendor ITN behaviour**
- Amazon Transcribe supports "Transcribing numbers" for **hi-IN in batch and streaming**. It also lists hi-IN with custom vocabulary (batch/streaming), custom language models (batch only), no PII redaction, and post-call Call Analytics., [AWS supported languages](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)
- Amazon number transcription is context-dependent ("8:30 a.m.", "$3.50", "1.5"). In languages without support, numbers come out as words. Punctuation is added automatically for all languages. The docs give no hi-IN specifics, such as lakh/crore grouping or Devanagari versus ASCII digits., [AWS how-numbers](https://docs.aws.amazon.com/transcribe/latest/dg/how-numbers.html)
- Azure ITN "converts verbalized forms into their corresponding symbolic written forms… The speech to text service completes this process and it's **not configurable**."
  - Results carry `LexicalForm` and `NormalizedForm` (ITN) properties alongside the display text and masked text.
  - The profanity filter applies to `Text`/`MaskedNormalizedForm`, but not to `LexicalForm`/`NormalizedForm`.
  - Examples are English only, and no locale list is given.
  - [Azure display-text-format](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/display-text-format)

### Inferences
- **Recipe 1: a pre-WER Devanagari normaliser in 30 lines, no dependencies (tested).** Apply it to both reference and hypothesis before romanisation. Keep a `strict` variant (only NFC, ZW cleanup, digits and punctuation) for "exact" WER, and a `lenient` variant for "script-tolerant" WER. Report both.
  ```python
  import re, unicodedata
  NUKTA, VIRAMA, ANUSVARA, CANDRABINDU = '़', '्', 'ं', 'ँ'
  NASAL_CLASS = {'ङ':'कखगघ','ञ':'चछजझ','ण':'टठडढ','न':'तथदध','म':'पफबभ'}
  _strict = re.compile('(' + '|'.join(f'{n}{VIRAMA}(?=[{c}])' for n,c in NASAL_CLASS.items()) + ')')
  def norm_dev(s, lenient=True):
      s = unicodedata.normalize('NFC', s)
      s = s.replace('ऩ','न'+NUKTA).replace('ऱ','र'+NUKTA).replace('ऴ','ळ'+NUKTA)
      s = re.sub('[​‌‍⁠﻿­]', '', s)
      s = s.translate(str.maketrans('०१२३४५६७८९', '0123456789'))
      if lenient:
          s = s.replace(NUKTA, '')            # ज़→ज, फ़→फ, ड़→ड
          s = s.replace(CANDRABINDU, ANUSVARA) # आँख→आंख
          s = _strict.sub(ANUSVARA, s)          # हिन्दी→हिंदी, सम्बन्ध→संबंध
      s = ''.join(' ' if unicodedata.category(c)[0] in 'PS' else c for c in s)  # P/S only, NEVER M
      return re.sub(r'\s+', ' ', s).strip().lower()
  ```
  Local results: "पच्चीस हज़ार रुपये॥" → "पच्चीस हजार रुपये"; "हिन्दी हिंदी" → "हिंदी हिंदी"; "क्‍या" with ZWJ → "क्या"; "१२३" → "123"; "नम्र" is left unchanged (not homorganic).
- Where nukta and chandrabindu folding helps: dropping the nukta merges ज/ज़, फ/फ़ and ड/ड़. This is right for WER on phone Hindi, because speakers and recognisers are inconsistent. It is **wrong for the name key** if Parakh's phonetic key already treats z/j or f/ph distinctly. Pick one policy and apply it to both sides.
- Ordering matters: run `norm_dev` *before* ITRANS romanisation. Otherwise ZWJ/ZWNJ and the precomposed-versus-decomposed nukta produce different romanisations of the same word.
- Never let Whisper's `BasicTextNormalizer` (or HF `WhisperProcessor.normalize`) touch Devanagari. If Parakh wants Whisper's English rules for Roman-script tokens, call `EnglishTextNormalizer` only on Latin-script tokens, after script detection.
- ITN: Amazon (hi-IN numbers on) and Azure (ITN not configurable) return digits and formatting on the display form. Azure's lexical form is the spoken-form string. The cheapest consistent policy is to **score WER on spoken form** (Azure `Lexical`; for others, run Parakh's own rule-based "digits → Hindi/English number words" on the hypothesis) and **score numbers/entities on written form** (Parakh's lakh/crore ITN applied to both sides, then canonical digits). Do not install NeMo/pynini under hackathon time pressure on a Mac; pip install is unsupported there.

### Gaps
- No vendor documents hi-IN ITN details: lakh/crore grouping ("1,50,000" vs "150,000"), Devanagari versus ASCII digits, or how Hinglish numbers ("twenty five hazaar") are rendered. This must be probed empirically with 5–10 clips per vendor.
- I did not check Google Cloud STT/Chirp hi-IN number formatting or Deepgram/ElevenLabs hi behaviour.
- I could not read the NeMo Hindi ITN grammar coverage per semiotic class (money, telephone, fractions) from the flattened table. The `whisper_normalizer` Indic fix status and the Vistaar `evaluation.py` normalisation are unverified.

## 2. Transliteration for evaluation and matching (Hinglish romanisation, T-WER, PIER, MER, PolyWER, SN-WER)

### Takeaway
The field has converged on canonicalising script before scoring: map one side to the other's script, or accept a set of variants per slot, then run normal Levenshtein. Separately, it reports the error rate on the "interesting" tokens: PIER for embedded-language words, KER for keywords. Parakh's romanise-then-fold design is SN-WER/T-WER-style. Its "names right" is PIER with points of interest = name tokens. Both have citable precedents.

### Cited Findings
- **SN-WER** (Pattnayak, MeLLM 2026 workshop at ACL, pp. 249–256):
  - Definition: SN-WER(R,H) = WER(T(R), T(H)), where T transliterates romanised tokens (detected by Unicode block) into the *reference* native script, with "standard Unicode, punctuation, and digit normalization".
  - Robust to transliterator choice: IAST vs ITRANS vs ICU Δ < 0.002, Hindi 0.421/0.420/0.421.
  - Token-collision rate < 0.1%.
  - Removes 67% of artificially injected romanisation inflation (Hindi 0.58).
  - Stays about as sensitive to real lexical errors (ΔSN/ΔWER ≈ 1.09).
  - Recommended as a companion to WER/CER, not a replacement.
  - [ACL Anthology PDF](https://aclanthology.org/2026.mellm-1.24.pdf)
- **PolyWER** (Kadaoui et al., MBZUAI, Findings of EMNLP 2024):
  - Each reference word has three variant fields: transcription, transliteration and translation.
  - In the DP, an exact match costs 0. A transliteration match costs CER(translit_ref, hyp) if ≤ α; the example uses α = 0.25. A translation match costs 1 − cosine (BERT) if ≥ β = 0.85. Otherwise the cost is 1.
  - It is more consistent with human judgement than WER, CER or a prior multi-reference WER.
  - Data: Mixat Arabic-English, about 15 h.
  - Code: [github.com/mbzuai-nlp/PolyWER](https://github.com/mbzuai-nlp/PolyWER)
  - [ACL Anthology PDF](https://aclanthology.org/2024.findings-emnlp.356.pdf)
- **PIER** (Ugan, Pham, Bärmann, Waibel; KIT; **preprint** arXiv 2501.09512, Jan 2025):
  - Align REF and HYP. Count an edit operation if its REF position is a point of interest.
  - PIER = |counted ops| / |points of interest|.
  - Default points of interest are the embedded-language words, identified automatically when scripts differ.
  - Insertion attribution is not fully specified.
  - Fisher Spanish-English example: fine-tuning on monolingual data moved WER 29.43 → 27.94 (better), while PIER moved 36.41 → 50.78 (much worse).
  - No Hindi-English test set.
  - Code: enesyugan/PIER-CodeSwitching-Evaluation
  - [arXiv html](https://arxiv.org/html/2501.09512v2)
- PIER has since been reused:
  - HiKE (Korean-English) reports PIER alongside MER, [arXiv 2509.24613](https://arxiv.org/pdf/2509.24613)
  - MUSCAT 2026 uses PIER, [arXiv 2604.15929](https://arxiv.org/pdf/2604.15929)
  - A Yoruba-English paper extends it to switch-point metrics, SETER and SPER@k, [arXiv 2609.11786](https://arxiv.org/pdf/2609.11786)
- **MER** (Mandarin-English mixed error rate):
  - Edit distance over Mandarin *characters* and English *words* as tokens.
  - Errors are attributed by the language of the reference token.
  - It was the ranking metric of the ASRU 2019 code-switching challenge; per-language rates were for reference only.
  - [ASRU 2019 challenge, arXiv 2007.05916](https://arxiv.org/pdf/2007.05916); [CS-Dialogue arXiv 2502.18913](https://arxiv.org/pdf/2502.18913)
- **KeyASRBench** (**preprint** arXiv 2611.10852, 7 Nov 2026):
  - Occurrence-based Keyword Error Rate (KER) over frozen whole-phrase annotations: names, products, versions.
  - Test set: 1,501 zh/en clips with 4,723 keyword occurrences.
  - Results: MER/WER 5.31–12.91% versus KER 13.61–33.81%, so keyword errors run 2–3× the global rate.
  - A model-blind 30-min control gives KER 10.65–27.31%.
  - [arXiv abs](https://arxiv.org/abs/2611.10852)
- Multi-reference and lattice for Hindi:
  - The HF Open ASR Leaderboard's Monsoon hi-IN set "ships a lattice: for each span of the transcript, the set of written forms accepted as correct". It scores OIWER, citing that "no normaliser can resolve" Hindi variation.
  - [HF blog](https://raw.githubusercontent.com/huggingface/blog/main/open-asr-leaderboard-global-south.md)
  - OIWER itself is covered in earlier notes.
- Rev's multi-reference "style-agnostic" WER (**preprint** arXiv 2412.07937, English):
  - Verbatim and non-verbatim references are compiled into a span-level union FST, and MWER is the minimum over paths.
  - "GOLD WER" scores only spans where the transcribers agree.
  - OpenAI API on Rev16: 11.21 (verbatim ref) and 9.62 (non-verbatim ref) → 5.45 MWER.
  - Tool: revdotcom/fstalign.
  - [arXiv html](https://arxiv.org/html/2412.07937v1)

### Inferences
- **Recipe 2: make Parakh's metric names match the literature.** Report "ST-WER" (script-tolerant WER, SN-WER-style) next to raw WER. Report "Name-PIER" = errors on name tokens / number of name tokens. Report "Name false-insertion rate" separately, because PIER leaves insertion attribution vague. Citing SN-WER and PIER gives judges recognisable anchors.
- **Recipe 3: soft substitution cost, PolyWER-style, about 20 lines in an existing Levenshtein.** In the DP, set the substitution cost to 0 if the romanised-and-folded tokens match. Set it to CER(a, b) if CER ≤ 0.25 *and* the tokens share Parakh's phonetic key. Otherwise set it to 1. This turns "rahul/raahul" into a near-0 cost but keeps "rahul/rohit" a full error.
- Direction choice: SN-WER maps into the native script, while MUCS T-WER maps English words into Latin (earlier notes). Parakh maps everything to Roman. For Hinglish phone calls that is defensible, because English loanwords and brand names are naturally Latin. It is also the only option when the reference itself is Roman. SN-WER's finding that transliterator choice changes scores by < 0.002 suggests the direction matters little for aggregate WER. Collisions (distinct words → the same romanisation) are the risk to measure: count them on the test set and report them, as SN-WER does (< 0.1%).
- Use MER only if Parakh switches to character-level scoring for Devanagari. For Roman-folded Hinglish, word-level ST-WER is the closer analogue.

### Gaps
- I found no peer-reviewed standard for Hinglish *romanisation conventions* (e.g., "aa" vs "a", "w" vs "v") used in ASR scoring. Practice is ad hoc variant folding or LLM equivalence judgement.
- PIER's handling of insertions next to a point of interest is not specified in the paper; check the GitHub code.
- I found no Hindi-English PIER results.

## 3. Metrics beyond WER (CER vs WER, entity metrics, false alarms, semantic and LLM metrics, multi-reference)

### Takeaway
For Indic, the defensible stack is layered:
1. WER and CER on normalised text, with CER at least as a supplement.
2. An entity-restricted error rate: NE-WER, B-WER/U-WER or KER.
3. A false-alarm term for hallucinated entities.
4. Optionally, an LLM equivalence judge.

The only Hindi-validated LLM rubric (LASER) forgives proper-noun and number *format* variants by design. Parakh should keep its deterministic entity metrics as primary and use any LLM judge only as a secondary "meaning preserved" score.

### Cited Findings
- **CER vs WER:** Thennal D K et al. (Findings of NAACL 2025) recommend CER as the primary metric, or at least a supplement, for multilingual ASR. In their human study CER correlated better with human judgement than WER, even for English; the human-eval data is released., [arXiv 2410.07400](https://arxiv.org/pdf/2410.07400); [ACL 2025.findings-naacl.277](https://aclanthology.org/2025.findings-naacl.277)
- **NE-WER** = (words wrongly transcribed inside named entities) / (words inside named entities in the reference), attributed to Garofolo et al. 1999. It correlates better than WER with keyword-spotting/IR outcomes but did not change system rankings. It ignores insertions outside entities, which cause downstream false alarms. Successor: ATENE (Ben Jannet et al., Interspeech 2015)., [Interspeech 2015 jannet15](https://www.isca-archive.org/interspeech_2015/jannet15_interspeech.pdf)
- **B-WER / U-WER:** WER restricted to words in or out of the biasing list. An inserted word counts toward B-WER if it is in the list, otherwise toward U-WER. Goal: lower B-WER without raising U-WER. This is standard in contextual-biasing papers., [arXiv 2104.02194](https://arxiv.org/pdf/2104.02194); [arXiv 2401.08835](https://arxiv.org/pdf/2401.08835)
- **ATWV:** the keyword-search false-alarm-aware metric of IARPA Babel and NIST OpenKWS. ATWV = 1 − mean over keywords of (P_miss + β·P_FA), with β ≈ 999.9, computed at the system's own threshold; MTWV uses the best threshold. A miss of a rare keyword costs more, while the false-alarm penalty is nearly constant., [NIST OpenSAT20 eval plan](https://www.nist.gov/system/files/documents/2020/04/15/2020_OpenSAT20_Eval_Plan_V1.5.pdf); [ICASSP13 IBM](https://mi.eng.cam.ac.uk/~mjfg/ICASSP13_ibm1.pdf)
- **SemDist** (Kim et al., Interspeech 2021, Meta):
  - 1 − cosine between RoBERTa mean-pooled sentence embeddings of reference and hypothesis; lower is better.
  - "This is the cat" scores 0.0077 and "This is a cap" 0.0157, though both have 25% WER.
  - Follow-ups use XLM-R.
  - [Interspeech kim21e](https://www.isca-archive.org/interspeech_2021/kim21e_interspeech.pdf); [arXiv 2110.05376](https://ar5iv.labs.arxiv.org/html/2110.05376)
  - A 2026 study found the best SemDist configurations agreed most with humans and WER least, on English., [arXiv 2609.21663](https://arxiv.org/pdf/2609.21663)
  - Embedding metrics handle alternate spellings poorly, per a search summary., [LASER arXiv](https://arxiv.org/html/2510.07437v1)
- **SeMaScore** (arXiv 2401.07506) combines an error-rate term with semantic similarity and reports about 41× the speed of BERTScore. I found no Indic evaluation., [arXiv](https://arxiv.org/html/2401.07506v2)
- **LASER** (Parulekar & Jyothi; arXiv 2510.07437; search results link an EMNLP 2025 main PDF, 2025.emnlp-main.1257, which I did not verify):
  - An LLM aligns words and classifies each mismatch, and the sentence score = 1 − penalty / reference words.
  - No penalty: numbers, abbreviations, compound words, transliterations, alternate spellings, proper nouns, slang. Minor (0.5): single-character or grammatical errors that keep the meaning. Major (1.0): meaning-changing errors.
  - Gemini 2.5 Pro reached about 94% correlation with human annotation on Hindi. Data: 172 Hindi IndicVoices sentences with SeamlessM4T output.
  - A LoRA Llama-3-8B pair classifier reached 88.69% accuracy.
  - [arXiv html](https://arxiv.org/html/2510.07437v1)
- **Sarvam** production layered metrics (vendor, Apr 2026):
  - LLM-WER/LLM-CER: alignment first, then an LLM judge for semantic or phonetic equivalence that "defaults to non-equivalence in any ambiguous case", with each token's contribution capped at 1.0.
  - An Intent Score and an Entity Preservation Score (0–1 over names, places, numbers, dates; 1.0 if none).
  - The judge is Gemini, at temperature 0 with a pinned version.
  - Suggested targets: Entity ≥ 0.90, or ≥ 0.95 for banking/medical; LLM-WER < 15%.
  - Re-run a 50-sample calibration set when the judge changes, and investigate shifts > 1 point.
  - [Sarvam blog](https://www.sarvam.ai/blogs/evaluating-indian-language-asr)
- Multi-reference and lattice scoring: see Q2. Monsoon hi-IN plus OIWER is the Hindi instance, and Rev MWER/GOLD WER the English instance. Rev notes multi-references cost about 2× in annotation., [arXiv 2412.07937](https://arxiv.org/html/2412.07937v1)

### Inferences
- **Recipe 4: Parakh's "names written but not said" is a false-alarm metric, so name it and normalise it like KWS does.** Report FA per call, or per 100 reference words, next to entity recall. Optionally fold both into an ATWV-like score: 1 − (miss_rate + β·FA_rate). Pick a β that reflects call-centre cost, e.g. "a wrong name is 3× worse than a missed name", rather than NIST's 999.9, which was tuned for rare-term search. State β explicitly.
- B-WER/U-WER maps directly onto Parakh if it passes a name list to recognisers that support biasing. Report "Name-B-WER drops, U-WER flat" as evidence that biasing does no collateral damage.
- An LLM judge à la LASER would mark a wrong-but-similar name as "proper noun, no penalty" unless the prompt is changed. If Parakh adds one, tell it explicitly that a different person name or a different number is a major error. Follow Sarvam's practice: temperature 0, pinned model, default to non-equivalent.
- CER: compute CER on the romanised-and-folded string as a secondary number. It is cheap (`jiwer.cer` or Levenshtein over characters) and blunts word-segmentation noise ("pachchees hazaar" vs "pachchees-hazaar").

### Gaps
- I found no published Indic results for SeMaScore or SemDist. LASER covers only about 172 Hindi sentences of read or extempore IndicVoices, not telephony.
- I found no standard Indic entity-level benchmark beyond IndicContextEval (earlier notes). KeyASRBench is zh/en only.

## 4. Regression suites, slice-based metrics and telephony conditions in production

### Takeaway
Public evidence on production "golden set" governance is thin. What does exist points to the same practice:
- Keep a frozen in-domain set with per-segment metadata.
- Report per slice (speaker region, device, codec, code-mixing) as well as the mean.
- Simulate telephony by downsampling to 8 kHz with a codec, not just low-pass.
- Do **not** "enhance" narrowband audio with neural super-resolution before ASR.

### Cited Findings
- The HF Open ASR Leaderboard Monsoon sets (VoiceArena guest authors with HF; the post itself is undated, mirrors date it 28 Aug 2026):
  - "Monsoon ships 18 columns per segment, of which 12 are metadata": gender, occupation, native district, device model, and so on.
  - Splits are speaker-disjoint.
  - A slice by five zonal councils showed that "Two systems that are indistinguishable on the leaderboard differ almost fourfold" in regional sensitivity.
  - [HF blog](https://raw.githubusercontent.com/huggingface/blog/main/open-asr-leaderboard-global-south.md)
- The Factors-affecting-Indic-ASR study (IISc/ARTPARK-affiliated authors incl. Prasanta Kumar Ghosh; **preprint** arXiv 2606.09335, Jun 2026):
  - Telephony recipes:
    - GSM 2G = downsample to 8 kHz → GSM 06.10 encode/decode → resample to 16 kHz.
    - "Narrowband 3G" = 3.4 kHz low-pass + 8 kHz resample.
    - "Wideband 4G" = 8 kHz low-pass + 16 kHz.
    - Opus 5G = Opus encode/decode.
    - Bit depth quantised to 12/10/8/6 bits.
    - Noise: white noise, competing speech, AudioSet non-speech.
  - Findings for Hindi (IndicConformer-hi, Vaani-Whisper-L-hi on FLEURS/Kathbath):
    - GSM consistently degrades WER, while narrowband/wideband stay close to 16 kHz and Opus degrades only marginally.
    - 10–12-bit audio is stable, with sharp degradation at ≤ 8 bits.
    - Classical resampling (linear, soxr-hq) costs a moderate loss, while neural restoration (VoiceFixer, AudioSR) "paradoxically worsen[s] WER".
    - Competing background speech causes the strongest degradation, and Whisper-based models are more robust to it.
  - [arXiv PDF](https://arxiv.org/pdf/2606.09335)
- Older codec study (NCC 2017, IISc): narrowband high-bit-rate codecs such as G.711 gave lower phone error rates than low-bit-rate codecs for most acoustic models., [Srinivasa NCC 2017](https://spire.ee.iisc.ac.in/assets/PDFs/papers_pdf/Srinivasa_NCC_2017.pdf)
- Vendor advice (Gladia, vendor, 25 Sep 2026):
  - Build a test set from your own production telephony audio, sliced by accent, language and codec, with codec read from SIP/SDP.
  - Test packet loss at 0/1/5/10% with NetEm.
  - Report entity-level error rates and diarisation error rate alongside WER, and run a blind cross-provider comparison.
  - It argues against upsampling 8 kHz to 16 kHz.
  - Its WER claims (Solaria-3 33.9% on Switchboard) are self-reported and not reproducible from the page.
  - [Gladia blog](https://www.gladia.io/blog/telephony-audio-robustness-why-8khz-narrowband-calls-break-generic-stt)
- AssemblyAI (vendor, anecdotal) reports that upsampling 8 kHz μ-law to 16 kHz added hiss that broke their VAD, and that sending native 8 kHz μ-law fixed it., [AssemblyAI blog](https://www.assemblyai.com/blog/mu-law-vs-a-law-text-to-speech-phone-calls)
- Academic support for slicing: per-group representative sets, and synthetic perturbations to expose group-specific weaknesses., [arXiv 2203.15591](https://arxiv.org/pdf/2203.15591v1.pdf)
- Targeted suites find "systematic deficiencies [that otherwise] remain undetected"., [AfriSpeech-MultiBench arXiv 2511.14255](https://arxiv.org/html/2511.14255v1)
- A longitudinal study of 16 systems from 2021–2025 found accent gaps did not clearly shrink., [Toronto longitudinal ASR](https://www.cs.toronto.edu/~fsamir/longitudinal_asr.pdf)

### Inferences
- **Recipe 5: a telephony condition in about 30 minutes, with no new dependencies beyond ffmpeg.**
  - Run `ffmpeg -i in.wav -ar 8000 -ac 1 -c:a pcm_mulaw tel.wav` (G.711 μ-law, 8 kHz). Then send `tel.wav` *as-is* to APIs that accept 8 kHz, or decode back to 16-bit PCM at 8 kHz, without neural upsampling.
  - For a GSM-like harsh condition, ffmpeg's `libgsm` codec is available if built in.
  - Python 3.10's `audioop.lin2ulaw/ulaw2lin` also works (deprecated in later Pythons).
  - Report clean vs G.711 vs GSM as three slices. This applies the Factors-paper protocol to Parakh's own clips.
- **Recipe 6: a minimal golden set for a solo builder.**
  - Freeze 30–60 clips with references, entity spans and slice tags: code-mix ratio (fraction of Latin-script tokens in the reference), number-heavy y/n, name count, channel (phone/app), noise y/n.
  - Store a JSON manifest with a hash of the audio and of the reference.
  - Every harness change re-runs the set. Fail the run if ST-WER rises by more than the bootstrap CI half-width, or if any previously-hit entity turns into a miss. That gives a "no regressions on entities" gate.
  - Print per-slice tables, as Monsoon does, rather than one mean.
- Vendor sample-rate handling differs (Amazon/Azure accept 8 kHz natively; the Gladia/AssemblyAI anecdotes warn against upsampling). Parakh should record which rate and codec it sent to each API in the run metadata, because that is a confound in cross-vendor comparison.

### Gaps
- I found no public write-up from Google, Amazon or Microsoft on internal ASR release-gating or golden-set governance. Public practice is mostly academic benchmarks and vendor blogs.
- I found no controlled G.711-specific WER numbers for Hindi; the Factors paper used GSM, low-pass and Opus.
- I did not verify per-vendor sample-rate recommendations for hi-IN telephony in docs (Google `phone_call` model availability for hi-IN, Azure 8 kHz handling).

## 5. Statistical practice for small test sets (bootstrap unit, McNemar for entity hits, MDE, how many mentions for a 5-point gain)

### Takeaway
Treat entity hits as paired binary outcomes (same mention, system A vs B) and use exact McNemar on the discordant pairs, with a call-level paired bootstrap as a cross-check. With Parakh-scale sets (50–100 entity mentions), only about 8–20-point differences are reliably detectable. A credible "+5 points names-right" claim needs roughly **150–470 entity mentions**, depending on how often the two systems disagree. With fewer, report the CI and call it directional.

### Cited Findings
- NIST SCTK `sc_stats` offers MAPSSWE (matched-pairs sentence-segment word error), McNemar (`mcn`), sign, Wilcoxon and ANOVA tests for systems run on identical data., [SCTK docs](https://people.csail.mit.edu/joe/sctk-1.2/doc/sclite.htm); [usnistgov/SCTK](https://github.com/usnistgov/SCTK/)
  - MAPSSWE is essentially a t-test on mean segment differences. McNemar applies to discrete right/wrong outcomes per item., [ISIP significance tutorial](https://isip.piconepress.com/projects/speech/software/tutorials/production/fundamentals/v1.0/section_04/s04_03_p06.html); [ISIP thesis notes](https://isip.piconepress.com/publications/ms_theses/2003/transcription_errors/thesis_questions.pdf)
  - A WER significance-test implementation exists, [talhanai/wer-sigtest](https://github.com/talhanai/wer-sigtest)
- McNemar power depends only on the discordant pairs. Connor (1987) sample size:
  - n = [(z₁₋α/2·√p_disc + z₁₋β·√(p_disc − p_diff²)) / p_diff]², where p_disc = p₁₀ + p₀₁ and p_diff = p₁₀ − p₀₁.
  - SAS notes Connor is slightly conservative and Miettinen slightly anticonservative.
  - Discordance usually needs pilot data.
  - [SAS PROC POWER paired-freq](https://support.sas.com/documentation/cdl/en/statug/66103/HTML/default/statug_power_details55.htm); [McNemar power tutorial](https://cttir.github.io/tutorials/tutorials/sample-size/power-mcnemar.html) (worked example: p₁₀ = 0.15, p₀₁ = 0.05 → about 79 pairs at 80% power)
- Bootstrap unit (from earlier notes, sources already verified there):
  - Utterance-level resampling gives narrower intervals than speaker-level, [Bisani & Ney ICASSP 2004](https://www-i6.informatik.rwth-aachen.de/~bisani/bootlog.html)
  - Correlated utterances call for a blockwise bootstrap, [arXiv 1912.09508](https://ar5iv.arxiv.org/html/1912.09508)
- SN-WER reports paired bootstrap CIs per language as standard practice for a new Indic metric., [MeLLM 2026](https://aclanthology.org/2026.mellm-1.24.pdf)

### Inferences
- **Computed here** (Connor formula, two-sided α = 0.05, 80% power; exact-McNemar power by 4,000-run simulation; script in scratchpad). Mentions needed for a **+5-point** gain in entity hit rate:

  | Discordant rate p₁₀+p₀₁ | A wins p₁₀ | A loses p₀₁ | Mentions needed |
  |---|---|---|---|
  | 0.05 | 0.050 | 0.000 | ~155 |
  | 0.07 | 0.060 | 0.010 | ~218 |
  | 0.10 | 0.075 | 0.025 | ~312 |
  | 0.15 | 0.100 | 0.050 | ~469 |
  | 0.20 | 0.125 | 0.075 | ~626 |

  - Simulated exact-McNemar power for +5 points with no losses: N=50 → 0.04; N=100 → 0.38; N=200 → 0.94.
  - With 2.5% losses: N=100 → 0.23; N=200 → 0.54; N=400 → 0.87.
  - Minimum detectable gain at 80% power: N=50 → 15–22 points; N=100 → 8–13 points; N=200 → 4–8.5 points; N=400 → 2–5.5 points (range = loss rate 0 to 5%).
- **Recipe 7: the stats Parakh should print.**
  - (a) A per-mention 2×2 table (A hit/B hit) and an exact McNemar p-value, computed with `math.comb` with no SciPy needed: p = min(1, 2·Σ_{i≤min(b,c)} C(b+c, i)/2^(b+c)).
  - (b) A call-level paired bootstrap of the difference in hit rate, resampling *calls*, not mentions, because mentions in one call share speaker and channel. 10k resamples; report the 95% CI.
  - (c) The MDE for the current N, using the table above, so judges see that "no significant difference" at N=60 means "under-powered", not "equal".
- Clustering: with m mentions per call and intra-call correlation ρ, the effective sample size shrinks by the design effect 1 + (m−1)ρ. This is a standard survey-statistics result, not sourced here. With 3 names per call and ρ = 0.3, 150 mentions behave like about 94, which is why the bootstrap resamples calls.
- For WER differences, keep the existing paired bootstrap from earlier notes. For false insertions (counts per call), use a paired bootstrap or a sign test on per-call FA counts rather than McNemar.

### Gaps
- I found no ASR-specific published power analysis for entity metrics, and no empirical intra-call correlation for name errors in Hindi telephony; the ρ used above is illustrative.
- The Connor formula is cited via a calculator page and SAS documentation, not the original 1987 paper.

## 6. Public Hindi/Hinglish telephony test sets with names or numbers usable within hours

### Takeaway
No free, permissively licensed, *telephony* Hindi test set with entity annotations exists. The fastest credible options:
- **Monsoon hi-IN** (CC-BY-4.0, 753 spontaneous phone-device clips with a variant lattice that already includes names and numbers; HF, Aug 2026). It is phone-recorded, but not necessarily over a phone call.
- **Gramvaani SLR118** eval (real phone calls, academic licence; earlier notes).
- Parakh's own clips, passed through Recipe 5's G.711 simulation.

### Cited Findings
- **Monsoon hi-IN** (`VoiceArena/MonsoonASR-Open-ASR-leaderboard-hi-IN`):
  - Licence "cc-by-4.0". One "test" split of 753 rows, clips 0.51–15 s, tagged conversational/spontaneous.
  - The lattice column holds per-slot variant spellings, including names ("हेमंत", "सोरेन"), numbers ("2nd", "1") and English loanwords in both scripts.
  - Metadata includes device manufacturer and model (vivo/OPPO/Xiaomi/Samsung), gender, native district and state, current city, and more.
  - Sampling rate and channel are not stated on the viewer page.
  - [HF dataset viewer](https://huggingface.co/datasets/VoiceArena/MonsoonASR-Open-ASR-leaderboard-hi-IN)
  - The blog says the public hi-IN split is 1.33 h with 468 speakers, and the 4.47 h private split is held out., [HF blog](https://raw.githubusercontent.com/huggingface/blog/main/open-asr-leaderboard-global-south.md)
  - The scorer is `voi-oiwer` on PyPI (earlier notes).
- **InfoBayAI Hindi Call-Center Audio (single-channel)**:
  - 8 kHz real call-centre audio, gated (you must share contact info).
  - The metadata says cc-by-4.0, but the card also says "research and educational purposes only". Hour counts are inconsistent (37.7 MB sample only).
  - Transcripts are unspecified, PII is muted, and there are no entity labels.
  - [HF card](https://huggingface.co/datasets/InfoBayAI/Hindi-Call-Center-Audio-Dataset-Single-Channel)
- **Commercial-only sets**:
  - Nexdata Hindi conversational telephone (8 kHz, 760 h; HF card returned 401), [HF](https://huggingface.co/datasets/Nexdata/Hindi_Conversational_Speech_Data_by_Telephone)
  - Appen HIN_ASR001 "scripted telephony", whose prompts include digits, natural numbers and personal/business/place names; recorded 2006, [Appen](https://www.appen.com/data-catalog/audio-catalogue/hin-asr001)
  - Defined.ai Hindi call-centre sets, [Defined.ai](https://defined.ai/datasets/hindi-call-center)
- **Gramvaani OpenSLR 118**: spontaneous telephone speech, about 61% at 8 kHz, 3 h eval, free for academic use (details in earlier notes)., [OpenSLR 118](https://openslr.org/118)

### Inferences
- **Recipe 8: an external sanity check in about 2 hours.**
  - `load_dataset("VoiceArena/MonsoonASR-Open-ASR-leaderboard-hi-IN")`. Pick about 100 clips whose lattice contains a name or a digit token. Run Parakh's recognisers.
  - Score with both `voi-oiwer` (the community metric) and Parakh's ST-WER and Name-PIER. Agreement between the two validates Parakh's scorer on third-party data.
  - Then run the same 100 clips through G.711 μ-law (Recipe 5) to create a "telephony" slice.
  - CC-BY-4.0 permits this with attribution. The metadata includes personal attributes (DOB, income), so do not display them in a demo.
- Names in Monsoon are incidental, not annotated entity spans. Parakh would need to derive "entity slots" from lattice slots containing capitalised Latin or name-like Devanagari, or hand-tag about 100 mentions, which takes about 1 hour.

### Gaps
- I could not confirm Monsoon's sampling rate, whether audio is raw device capture or call audio, or gating status (the viewer did not show a gate).
- The InfoBayAI terms conflict, and Nexdata's card was inaccessible.
- I found no public Hinglish telephony set with entity spans and an open licence.
