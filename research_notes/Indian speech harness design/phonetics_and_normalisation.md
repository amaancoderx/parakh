# Cross-script phonetic matching for Indian names + Indian number/format normalisation (Python, offline, hackathon-grade)

Research date: 2026-11-21. Constraint lens: Python 3.10 on a Mac, offline, usable within hours. All claims below carry inline sources. Ranking and design advice is in the "Inferences" subsections.

## Q1. Phonetic matching tools: which handle Devanagari<->Latin, what accuracy is reported, and how to score and threshold candidates against distractors?

### Takeaway
The only purpose-built, drop-in, pure-Python option is `misheard` (formerly `indic-phonetic`). It is MIT-licensed, has no dependencies, handles Devanagari, Tamil and Latin, uses an articulatory-feature weighted edit distance, and suggests accept/read-back/re-ask thresholds. It is also one week old, alpha, has 0 stars and has never been evaluated on real ASR output, so vendor it and tune its thresholds on your own distractor set. The best fallbacks are a DIY pipeline (deterministic Devanagari->Roman, then phonetic key or weighted edit distance with RapidFuzz-style scoring) and, for recall, indexing several romanisations of each contact. IndicXlit is accurate enough only as a top-k candidate generator, and its fairseq dependency is painful. Symphonym embeddings are experimental and untested on Indian names.

### Cited Findings

**`misheard` (PyPI `misheard`; old name `indic-phonetic`)**
- Purpose: "Match Indian names and places by how they **sound**, not how they are spelled, across Devanagari, Tamil and Roman script." It is alpha (0.1), and "The API may still change before 1.0.", [GitHub trivedi-aman/misheard](https://github.com/trivedi-aman/misheard)
- Algorithm (from the README):
  1. Transliterate Devanagari and Tamil into one phonetic Roman form. Hindi schwa deletion is applied, Tamil stops are voiced between vowels, and retroflexes stay marked (ṭ ḍ ṇ ḷ ṛ).
  2. Tokenize into sounds, first folding English-style spellings (x->ks, doubled letters).
  3. Score substitutions by articulatory features (place, manner, voicing, aspiration; vowel height, backness, length).
  4. Override costs from a confusion table, `data/confusions.csv` (v/w, t/ṭ, ph/f, Tamil k/g).
  5. Run a weighted edit distance in which dropping a silent *a* or an *h* is cheap.
  6. Handle names: titles and honorifics are ignored, initials match words with the same first letter, and word order is tolerated at a small cost., [GitHub](https://github.com/trivedi-aman/misheard)
- API: `distance(a,b)` (0 means the same sounds), `Matcher(references).best_match(heard, top=3)` (entries may be `(key, text)` pairs so aliases share a key), `explain(a,b)`, a `Confusions` class (`default()`, `.merged()`, `.without()`, `from_csv()`), helpers `to_roman`, `script_of` and `tokenize`, and a CLI. Example distances: `distance("Barmer","बाड़मेर")`=0.4, `distance("Barmer","Baadmer")`=0.6, `distance("Mohan","Rohan")`=1.7., [GitHub](https://github.com/trivedi-aman/misheard)
- Thresholds: none are built in. The README gives example values from the project it was extracted from: accept below ~0.8 **and** at least 1.0 ahead of the next candidate; read back below 1.8; otherwise ask again. It says to tune these on your own data., [GitHub](https://github.com/trivedi-aman/misheard)
- Benchmark: 782 items (300 synthetic people, 745 Indian districts with aliases). misheard scores 100% top-1 on every subset. Levenshtein scores 92.0–99.6% and Metaphone 74.0–97.6% (handwritten places: Levenshtein 92.0%, Metaphone 74.0%). The README cautions that none of the items are real STT output, that the rule-generated variants use the same confusions the engine models, and that the author wrote the handwritten items. Speed is ~5 ms per lookup against 780 places, versus 0.1 ms for Levenshtein., [GitHub](https://github.com/trivedi-aman/misheard)
- Limitations: only Devanagari, Tamil and Latin (anything else raises `UnsupportedScriptError`); not a general transliterator (the README points to indic-transliteration or IndicXlit for running text); confusion table tuned for all-India; "No real speech-to-text evaluation yet". MIT; core is "Pure Python, no dependencies"; 0 stars, 14 commits., [GitHub](https://github.com/trivedi-aman/misheard)
- `indic-phonetic` 0.1.1 was released Nov 14, 2026 and 0.1.0 on Nov 13, 2026. It has been renamed (`pip install misheard`) and is classified "7 - Inactive". It requires Python >=3.10 and is MIT. The wheel is 2.5 kB. PyPI flags a **"Change of provenance"**: 0.1.1 was built from a different repo and workflow than 0.1.0, which PyPI says "may also indicate that the release files have been compromised"., [PyPI indic-phonetic](https://pypi.org/project/indic-phonetic/)

**`indic-er` (GitHub KaranNMakim/indic-er, not on PyPI)**
- An entity-resolution service for messy Indian names, businesses and addresses. The pipeline is: script detection; rule-based transliteration tables for Devanagari, Gujarati and Tamil; honorific and legal-suffix stripping; an "Indic phonetic key"; blocking on five keys; eight weighted pairwise features; an "evidence gate" that requires non-name evidence before a merge; and conflict-aware clustering. The matching core makes no LLM calls. Embeddings are future work., [GitHub indic-er](https://github.com/KaranNMakim/indic-er)
- Accuracy on 5,000 synthetic records: pairwise P 0.981 / R 0.933 / F1 0.957, against an exact+fuzzy baseline F1 of 0.074. Results are on the project's own synthetic noise model. Dependencies include FastAPI, NetworkX and SQLite. **No software licence is shown.** 0 stars, 5 commits., [GitHub indic-er](https://github.com/KaranNMakim/indic-er)

**`codemix-restore-shunyalabs` (PyPI; ShunyaLabs)**
- "Restore English words from transliterated Indic script in code-mixed ASR output". It uses a five-stage pipeline: abbreviation and compound pre-passes; three-tier romanisation (optional neural IndicXlit, then Aksharamukha, then built-in phoneme maps); an HMM/Viterbi language tagger; optional neural back-transliteration; and reconstruction. It covers 24 languages and 12 scripts with a 30k-word English dictionary. API: `ScriptRestorer().restore(text, lang="hi")`, with `return_details=True`, `use_neural=False` and `use_viterbi=False` options., [PyPI JSON](https://pypi.org/pypi/codemix-restore-shunyalabs/json)
- MIT, Python 3.10+, v0.4.0. All releases came on 2026-03-16..19, with no later release seen. Core dependencies: `aksharamukha>=2.0`, `metaphone>=0.6`, `symspellpy>=6.7`. Neural mode needs torch plus `fairseq==0.12.2` and `ai4bharat-transliteration`, installed manually with `--no-deps`., [PyPI JSON](https://pypi.org/pypi/codemix-restore-shunyalabs/json)

**Symphonym (arXiv 2601.06932)**
- "Universal Phonetic Embeddings for Cross-Script Toponym Matching" by Stephen Gadd. Place names from 36 writing systems are mapped to a 128-d phonetic space. A Teacher trained on IPA articulatory features is distilled into a character-level Student, which needs no language ID or phonetic resources at inference. It was trained on 73.5M toponyms (GeoNames, Wikidata, Getty TGN). v1 is from 11 Jan 2026; v5 was revised 5 Oct 2026., [arXiv](https://arxiv.org/abs/2601.06932)
- Results: Recall@1 89.3% and MRR 92.8% on MEHDIE (medieval Hebrew/Arabic toponyms); articulatory features alone reach 45.0% MRR. In v5 the author found the encoder admitted 70.5% of random anagrams past the retrieval gate; targeted negatives cut this to 5.0%. The paper says "string metrics remain preferable for matching within the Latin script". The abstract reports no Devanagari or Indian-name results. Models and data are on Zenodo (doi 10.5281/zenodo.22767194); no software licence is stated on the arXiv page., [arXiv](https://arxiv.org/abs/2601.06932)

**AI4Bharat IndicXlit / Aksharantar (`ai4bharat-transliteration`)**
- MIT (code and models). The model is a ~11M-parameter transformer (6+6 layers, embedding 256). Aksharantar has 26M word pairs across 20 Indic languages. Hindi top-1 accuracy: en->hi 60.56 (Dakshina), 55.59 (Aksharantar native words), 58.87 (Aksharantar named entities); hi->en 52.30 (native words), 59.22 (named entities)., [GitHub IndicXlit](https://github.com/AI4Bharat/IndicXlit)
- PyPI latest is 1.1.3, uploaded 2022-09-14, so it is stale. It requires `fairseq` (unpinned) among many other dependencies. The API is `XlitEngine` with `beam_width` (default 4), `topk` (default 4), `rescore` (dictionary rerank, default True), and `src_script_type="indic"` for Indic->Roman. Known install errors include numpy binary incompatibility and a Cython rebuild error., [PyPI JSON](https://pypi.org/pypi/ai4bharat-transliteration/json)
- fairseq pain points: old fairseq does not support Python 3.11+; omegaconf conflicts with 3.11 dataclasses; fairseq 0.12.2 pins `omegaconf<2.1`, which clashes with hydra-core. One HF model card says the IndicXlit fairseq codebase is incompatible with Python 3.12. A third-party ctranslate2 port claims to avoid fairseq, but that claim is unverified., [LASER issue #280](https://www.github.com/facebookresearch/LASER/issues/280); [fairseq issue #5191](https://www.github.com/facebookresearch/fairseq/issues/5191); [HF all-indic-transliteration](https://huggingface.co/Singla0009/all-indic-transliteration)

**`indic-transliteration` (sanscript)**
- MIT. The latest version is 2.3.82, so the package is actively released. Core dependencies: regex, typer, toml, roman, tqdm., [PyPI JSON](https://pypi.org/pypi/indic-transliteration/json)
- It provides deterministic scheme-to-scheme transliteration (HK, ITRANS, Velthuis, IAST, OPTITRANS, Devanagari, Telugu, …) via `transliterate(data, sanscript.ITRANS, sanscript.DEVANAGARI)`. `to_lay_indian` simplifies OPTITRANS (e.g. "taM jitvA" -> "tam jitva"). There is **no** casual-spelling-to-Devanagari converter and no detect module is documented., [GitHub indic_transliteration_py](https://github.com/indic-transliteration/indic_transliteration_py)

**Phoneme-level route: epitran + PanPhon (+ ALINE)**
- epitran is MIT and supports Hindi (`hin-Deva`). English G2P "requires the installation of the freely available CMU Flite" (`lex_lookup`). The Mac build note says to change `cp -pd` to `cp -pR` in the Makefile if `make install` fails. 1,521 commits; 35 open issues., [GitHub epitran](https://github.com/dmort27/epitran)
- PanPhon is MIT with 342 stars. `panphon.distance.Distance` offers `feature_edit_distance`, `weighted_feature_edit_distance`, `hamming_feature_edit_distance`, `dolgo_prime_distance` and `fast_levenshtein_distance`. All inputs must be IPA., [GitHub panphon](https://github.com/dmort27/panphon)

**Classic phonetic codes**
- `abydos` includes Beider-Morse, Double Metaphone, Daitch-Mokotoff, NYSIIS, Caverphone, MRA and more. It is **GPLv3+**. The last release is 0.5.0 (2020-01-11), and the README says it "should run on Python 3.5-3.8"., [PyPI JSON abydos](https://pypi.org/pypi/abydos/json)
- `jellyfish` (MIT) latest 1.3.0 has `requires_python >=3.11`, so it does not install on Python 3.10; an older release is needed., [PyPI JSON jellyfish](https://pypi.org/pypi/jellyfish/json)
- `libindic-soundex` is LGPL-3.0. It is an Indic Soundex that compares across Indic scripts (the examples show Kannada vs Devanagari), and `compare()` returns 1, -1 or 2. No releases are published., [GitHub libindic/soundex](https://github.com/libindic/soundex)
- Older literature: "Soundex does not account for vowels and hence is not accurate for cross-lingual matching". Cross-script matching needs either a common phonemic representation or transliteration into English followed by a phonetic-equivalence check. Romanised Hindi names have user-developed spellings that "cannot be easily captured through rules"., [Search summary of ACL Anthology items, e.g. I08-5014](https://preview.aclanthology.org/fix_video/I08-5014.pdf); [W12-6103](https://aclweb.org/anthology/W12-6103.pdf) (the search tool summarised these; the PDFs were not read in full)

**LLMs as cross-script name matchers (caution)**
- "Same Entity, Different Script" (arXiv 2610.31407, 22 Oct 2026) used 601 audited Devanagari/Latin person-name pairs. Qwen2.5-7B's same-person accuracy fell from 35.1% (Latin) to 8.5% (Devanagari), while different-person accuracy stayed above 98%. A Malayalam replication gave 5.3%., [arXiv](https://arxiv.org/abs/2610.31407)

**Thresholding evidence from NE-correction work**
- Generative Annotation NEC keeps entities above a retrieval probability of 0.3, with at most 5 per segment. It reports that a higher-recall, lower-precision retrieval threshold gives the best final correction., [arXiv HTML 2508.20700v2](https://arxiv.org/html/2508.20700v2)

### Inferences

**Ranked shortlist for Step 1 (retrieval of the closest contact or place by sound):**
1. **`misheard`**: the primary scorer. It is pure Python, MIT, handles Devanagari<->Latin directly, and supports aliases. It already encodes the spelling variants you care about (ph/f, v/w, dropped schwa and h, doubled letters). Because the package is days old with a provenance warning and 0 stars, **pin the version and read the ~2.5 kB source, or vendor it into the repo**. At ~5 ms per lookup, 1,000 contacts is ~5–7 ms per query, which is fine. The pitfall is that Telugu, Kannada, Bengali and other scripts raise errors: wrap the call and fall back.
2. **DIY fallback or ensemble**: `indic-transliteration` (Devanagari -> ITRANS/OPTITRANS, then `to_lay_indian`) plus a hand-written fold to a skeleton key, scored with normalised Levenshtein or Jaro-Winkler (e.g. RapidFuzz, not verified here). Do your own schwa deletion; misheard's README treats it as necessary for Hindi. The blend is cheap and makes a good second opinion. Use it for tie-breaking or as an alternate score feature.
3. **IndicXlit (topk=4–8) offline index expansion**: precompute several romanisations of each Devanagari contact name, or several Devanagari forms of each Latin name. Do this in a separate Python 3.8–3.10 venv or a one-off script and cache the results to JSON, so fairseq never enters the main harness. Top-1 is only ~52–60% for Hindi, so never trust a single output; use it only to widen recall.
4. **epitran + PanPhon**: the phoneme-level route is principled, but English G2P depends on Flite (a C build) and on English pronunciation rules that may anglicise Indian names. Hindi-only (`hin-Deva`) is easy. This route is worth it only if misheard underperforms.
5. **Symphonym embeddings**: experimental for this use. It is not evaluated on Indian names, it had a history of anagram false positives, the paper itself prefers string metrics within Latin, and the licence is unclear. Skip it for a 28-hour build.
6. **Skip or avoid**: abydos (GPLv3, dead since 2020, Python 3.8 ceiling); Soundex variants, including libindic-soundex (vowel-blind, and LGPL); `jellyfish` 1.3.0 on Python 3.10 (pin <1.3 if needed); `indic-er` as a dependency (no licence; borrow ideas only, such as honorific stripping and the evidence gate).
- `codemix-restore-shunyalabs` (non-neural mode) is useful as a **pre-step**, not as a matcher. Run it before NE matching and normalisation to convert Devanagari-transliterated English words (e.g. "डॉक्टर", "हाईटेक") back to Latin. Watch its dependency weight (aksharamukha) and its tiny maintenance window (March 2026 only).

**Scoring and threshold recipe that rejects distractors:**
- Use two stages. (a) A high-recall shortlist: top-5 over all aliases (for example, misheard distance <1.8), mirroring the NEC finding that high-recall retrieval feeds the best final correction. (b) An accept rule with an **absolute threshold plus a margin over the runner-up**, as misheard suggests (<0.8 with a gap of ≥1.0). Otherwise emit "uncertain" and leave the span untouched, or offer the LLM a constrained choice.
- Score per token, then aggregate across multi-word names (first and last name). Allow initials and word-order swaps; misheard already does this.
- Add a length-normalisation sanity check. Short names such as "Ravi" and "Ravi Kumar" can collide, so require that the span's token count is compatible.
- Calibrate on a quick synthetic set built from the real contact list. Include true variants (Sreenidhi/Srinidhi, Mohammed/Muhammad, Hitech/Hitec, Devanagari forms) and minimal-pair distractors (Mohan/Rohan, at distance 1.7 in misheard, which sits just under the 1.8 read-back line). Sweep the thresholds to reach the target false-accept rate.
- Do not let an LLM decide cross-script identity unaided: same-person accuracy collapses on Devanagari in 2610.31407. Give it the deterministic shortlist and scores, and require it to choose from the list or "none".

### Gaps
- No independent or real-ASR evaluation exists for misheard, indic-er or codemix-restore. All reported accuracy comes from self-built synthetic sets.
- The `misheard` PyPI page itself failed to load, so I could not confirm the latest version number or release date (indic-phonetic 0.1.1 says it was renamed on Nov 14, 2026).
- I could not find Symphonym's software or model licence, nor any Indian-name evaluation.
- No paper found evaluates Double Metaphone or Beider-Morse adapted to Indian names. RapidFuzz and the `metaphone` package were not verified in this research.
- No published head-to-head exists for Hindi/Indian-English names (misheard vs IndicXlit vs PanPhon vs embeddings) on spoken data.

## Q2. Evidence from ASR named-entity-correction papers: which phonetic retrieval works best (phoneme edit distance vs grapheme vs embeddings vs audio)?

### Takeaway
Phonetic-level edit distance (PED) is the standard, strong, cheap baseline in recent NEC work: A-STAR uses it, and Apple's phonetic-retrieval contextualisation is built on the same idea. Audio-based retrieval (TTS'd entities against the ASR audio, through a Whisper encoder) clearly beats PED only when the misrecognition differs greatly in written form. That evidence is all Mandarin. No paper found compares these methods on Indian languages or Hinglish. For a hackathon, phoneme- or sound-level edit distance plus an LLM choosing among a shortlist is the evidence-backed design.

### Cited Findings
- **Generative Annotation NEC** (Luo et al., EMNLP 2025, arXiv 2508.20700):
  - Retrieval method: entities are TTS'd and encoded with a Whisper-base encoder plus a CNN. Attention against the speech segment then scores whether each entity is present (threshold 0.3, ≤5 candidates).
  - Language and data: Mandarin; AISHELL with 3,101 entities, a 50-entity Word Form Variation set, and a self-built BuzzWord set.
  - NE recall (Whisper / PED-NEC / PED+GL / SS+GL):

    | Test set | Whisper | PED-NEC | PED+GL | SS+GL |
    |---|---|---|---|---|
    | AISHELL | 70.85 | 83.34 | 84.34 | 87.31 |
    | Word Form Variation | 25.4 | 50.79 | 50.85 | 86.51 |
    | BuzzWord | 12.22 | 61.82 | 79.96 | 87.47 |

  - Reading of the results: with the correction model held fixed, retrieval choice matters little on standard data (84.34 vs 87.31) and a lot on large word-form variation (50.85 vs 86.51).
  - Code: github.com/L6-NLP/Generative-Annotation-NEC., [arXiv HTML](https://arxiv.org/html/2508.20700v2); [abstract](https://arxiv.org/abs/2508.20700)
- **A-STAR / RASTAR** (An et al., arXiv 2602.12287, Jan 2026): a rephrasing LM does NER, then retrieval by "phonetic-level edit distance", then an adaptive chain-of-thought reasoning model corrects. It reports relative NE-CER reductions of 17.96% (AISHELL-1) and 34.42% (Homophone). The abstract compares no retrieval types and links no code., [arXiv](https://arxiv.org/abs/2602.12287)
- **RECOVER** (Kumar & Sachdeva, EMNLP 2026 Industry, arXiv 2603.16411): an agentic post-ASR entity correction. It uses multiple ASR hypotheses, entity retrieval, LLM corrections under constraints, deterministic guardrails, and an LLM critic feedback round. There are five strategies (1-Best, Entity-Aware Select, ROVER, LLM-Select, Adaptive Routing), and LLM-Select is best. Results: up to 49% relative entity-phrase WER reduction and up to +14 pp entity recall over Whisper-large-v3, with overall WER preserved. The abstract does not describe the retrieval method., [arXiv](https://arxiv.org/abs/2603.16411)
- **Apple, "Contextualization of ASR with LLM using phonetic retrieval-based augmentation"** (arXiv 2409.15353): the LLM first detects the entity without context, then phonetically similar entities are retrieved from a **personal database** and fed back to the LLM. It reports up to 30.2% relative WER reduction and 73.6% relative NE error reduction on a voice-assistant task., [arXiv](https://arxiv.org/abs/2409.15353)
- The PED family is described as fast and lightweight, and DANCER reports ~7% CER reduction over a PED baseline on homophone sets. Zhou et al. (Interspeech 2022) represent pronunciation as fixed-dimensional vectors and combine them with BERT semantic embeddings in a weighted sum., [search summary](https://www.isca-archive.org/interspeech_2022/zhou22h_interspeech.pdf); [arXiv 2403.17645](https://arxiv.org/pdf/2403.17645.pdf) (this item comes from a search summary; the PDFs were not read in full)

### Inferences
- Apple's setup (personal contact DB, detect then phonetic-retrieve then LLM-decide) is the closest analogue to this harness, and it supports the plan: deterministic phonetic shortlist, then LLM selection under constraints, then guardrails.
- RECOVER's guardrails-plus-select design matches the "reject distractors" requirement: let the LLM choose only among retrieved candidates or "no change", and apply deterministic guardrails such as the margin threshold.
- If the ASR API returns n-best or alternates, querying the retriever with each hypothesis and taking the best score is cheap and mirrors RECOVER's multi-hypothesis evidence.
- Audio-based retrieval (SS) is the only approach shown to fix large written-form mismatches. It needs audio access, TTS of every contact, and a trained model, so it is out of scope for 28 hours. Cheap substitutes are a richer confusion table and multiple romanisations per contact.

### Gaps
- No NEC paper found evaluates on Indian languages, Hinglish or cross-script (Devanagari<->Latin) entities. All quantitative retrieval comparisons are Mandarin.
- Neither the RECOVER nor the A-STAR abstract gives a head-to-head of phoneme ED vs grapheme ED vs embeddings. The full texts were not read.
- I could not read the exact NPD definition in Apple's paper.

## Q3. Indian number/format normalisation (ITN): which tools handle lakh/crore, Hindi number words (dhai/dedh/saadhe/sava/paune), "double/triple", phones, "at the rate", UPI, PAN/IFSC/pincode, times, dates, ₹?

### Takeaway
NVIDIA NeMo text processing (Apache-2.0, WFST/Pynini) is the only mature open-source ITN covering both Devanagari Hindi and English.
- **Hindi (`hi`)**: cardinals with lakh/crore/arab, the fraction words saadhe/sava/paune/dedh/dhai in numbers, money and time, telephone digit strings (including English digit words), dates, measures and more.
- **English (`en`)**: crore/lakh cardinals, "double" digit strings and "at/dot" email.
- **Caveats**: Hindi ITN outputs Devanagari digits without grouping; input must be Devanagari; macOS needs conda-forge pynini.

No tool found handles "at the rate", "triple", UPI, PAN, IFSC or pincode explicitly. Build those as a small deterministic regex/rule layer, and either call NeMo as a sub-module or reimplement the handful of patterns you need.

### Cited Findings

**NVIDIA NeMo text processing (`pip install nemo_text_processing`)**
- Apache-2.0. Pip install works on Linux x86_64; **pip installs on macOS and Windows are not supported because of Pynini**. On macOS, install pynini from conda-forge (`conda install -c conda-forge pynini=2.1.6.post1`). The recommended environment is a conda env with Python 3.10., [GitHub NeMo-text-processing](https://github.com/NVIDIA/NeMo-text-processing)
- ITN language directories: ar, de, en, es, es_en, fr, he, **hi**, **hi_en**, hy, ja, ko, **mr**, pt, ru, sv, vi, zh., [GitHub ITN tree](https://github.com/NVIDIA/NeMo-text-processing/tree/main/nemo_text_processing/inverse_text_normalization)
- Hindi ITN taggers: cardinal, date, decimal, fraction, measure, money, ordinal, punctuation, telephone, time, whitelist, word. Test files also cover address., [hi taggers](https://github.com/NVIDIA/NeMo-text-processing/tree/main/nemo_text_processing/inverse_text_normalization/hi/taggers); [hi tests](https://github.com/NVIDIA/NeMo-text-processing/tree/main/tests/nemo_text_processing/hi/data_inverse_text_normalization)
- Hindi cardinal test cases (verbatim): "एक लाख एक~१००००१", "तीन करोड़~३०००००००", "एक अरब दो करोड़ तेईस लाख पैंतालीस हज़ार पाँच सौ सड़सठ~१०२२३४५५६७", "सवा सात सौ~७२५", "साढ़े सात हज़ार~७५००", "डेढ़ सौ~१५०", "ढाई सौ~२५०", "साढ़े सोलह सौ~१६५०". Outputs are **Devanagari numerals with no separators**., [test_cases_cardinal.txt](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/hi/data_inverse_text_normalization/test_cases_cardinal.txt)
- Hindi time test cases: "ढाई बजे~२:३०", "डेढ़ बजे~१:३०", "साढ़े पाँच बजे~५:३०", "सवा चार बजे~४:१५", "पौने पाँच~४:४५", "दो बजकर ग्यारह मिनट~२:११", "डेढ़ घंटा~१:३०"., [test_cases_time.txt](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/hi/data_inverse_text_normalization/test_cases_time.txt)
- Hindi money test cases: "साढ़े छः लाख रुपए~₹६५००००", "ढाई करोड़ रुपए~₹२५००००००", "पौने पंद्रह लाख रुपए~₹१४७५०००", and spelling variants रुपये/रुपए/रुपेया/रुपिया. Output is ₹ plus Devanagari digits **without** Indian grouping., [test_cases_money.txt](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/hi/data_inverse_text_normalization/test_cases_money.txt)
- Hindi telephone test cases: digit-by-digit Hindi ("नौ आठ सात छह…~९८७६५४३२१०"), "प्लस नौ एक …~+९१ ९८७६५४३२१०", and English digit words ("zero one three three six…~०१३३६२३४५६७"). **No डबल/ट्रिपल cases**., [test_cases_telephone.txt](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/hi/data_inverse_text_normalization/test_cases_telephone.txt)
- English ITN cardinal includes "twenty one crore ninety eight lakh thirty six thousand five hundred and ninety three~219836593", with no commas in the output., [en test_cases_cardinal.txt](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/en/data_inverse_text_normalization/test_cases_cardinal.txt)
- English telephone ITN handles "double": "double oh three…~003-123-5678", "four three two double seven…double zero five~432 7732 143214 3005", and "plus nine one…~+91 123-123-5678". It formats in US 3-3-4 style. **"Triple" does not appear** in the tests., [en test_cases_telephone.txt](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/en/data_inverse_text_normalization/test_cases_telephone.txt)
- English electronic ITN: "a dot b c at g mail dot com~a.bc@gmail.com", "a s d f one two three at a b c dot com~asdf123@abc.com", plus URLs. **"at the rate" does not appear.**, [en test_cases_electronic.txt](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/en/data_inverse_text_normalization/test_cases_electronic.txt)
- A `hi_en` (Hindi-English code-mixed) ITN directory exists with `taggers/tokenize_and_classify.py` and verbalizers. Its expected input script and classes are undocumented on the page., [hi_en tree](https://github.com/NVIDIA/NeMo-text-processing/tree/main/nemo_text_processing/inverse_text_normalization/hi_en)

**Lightweight Python word->number libraries**
- `number-parser` (BSD), last release 0.3.2 on 2023-03-28. Cardinals cover English, **Hindi**, Spanish, Ukrainian and Russian; ordinals are English only. `parse_number("चौदह लाख बत्तीस हज़ार पाँच सौ चौबीस", language='hi')` returns 1432524, so लाख works. Crore is not documented., [PyPI JSON number-parser](https://pypi.org/pypi/number-parser/json)
- `text2num` (MIT, Rust core, 3.1.0) supports Danish, Dutch, English, French, German, Italian, Portuguese and Spanish. There is **no Hindi and no lakh/crore**. macOS arm64 wheels exist only for Python 3.11–3.13; macOS on 3.8–3.10 is marked unsupported., [PyPI JSON text2num](https://pypi.org/pypi/text2num/json)
- The original `word2number` lists only standard (million/billion) terms. The `WordToNumber` fork adds lakh/crore/arba, e.g. 'two crore fifty lakh' -> 25000000., [PyPI WordToNumber](https://pypi.org/project/WordToNumber/) (from search summary); [PyPI word2number](https://pypi.python.org/pypi/word2number)
- Number->words (TN direction, useful for generating test variants) with Indian English lakh/crore: `numbers2words`, `indic-num2words`, `currency-to-words`; `num2words` has `lang_EN_IN`., [PyPI numbers2words](https://pypi.org/project/numbers2words); [PyPI indic-num2words](https://pypi.org/project/indic-num2words/1.2.2); [num2words lang_EN_IN](https://sources.debian.org/data/main/p/python-num2words/0.5.9-1/num2words/lang_EN_IN.py) (from search summary)

**Sarvam (API, not offline)**
- STT `mode` takes transcribe, translate, verbatim, translit or codemix, on saaras:v3/v4 only. "transcribe" applies "proper formatting and number normalization". "verbatim" gives an exact transcription "without normalization, preserving filler words and spoken numbers as-is". "codemix" keeps English words in Latin and Indic words in native script. saaras:v4 is the default. REST takes audio under 30 s., [Sarvam STT docs](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe) (from search summary)
- Sarvam Transliterate API: `numerals_format` is `international` (0-9, the default) or `native`. `spoken_form=true` converts written text to spoken form, e.g. "9:30am" -> "साढ़े नौ बजे" (the TN direction; no effect when the target is en-IN). `spoken_form_numerals_language` is native or english., [Sarvam transliterate docs](https://docs.sarvam.ai/api-reference-docs/text/transliterate)

### Inferences

**Ranked shortlist for Step 2:**
1. **Own deterministic rule layer (regex plus small lexicons) as the backbone.** NeMo-quality coverage is not needed for the target formats, and the fiddly Indian bits are missing from every tool anyway:
   - "double/triple X" expansion, handled before digit joining;
   - "at the rate (of)" -> "@" and "dot" -> "." inside email or UPI contexts;
   - UPI `handle@bank`;
   - PAN (5 letters, 4 digits, 1 letter), IFSC (4 letters, '0', 6 alphanumerics) and pincode (6 digits, first non-zero). These are well-known public formats, not verified in this research.
   - Indian digit grouping for ₹ (₹12,34,567);
   - romanised Hindi fraction words (saadhe/sava/paune/dedh/dhai/paav) applied to hazaar/lakh/crore and to "baje".
   Apply the NeMo Hindi test cases above as the spec and copy them as unit tests. The arithmetic (saadhe = +0.5, sava = +0.25, paune = −0.25 of the unit, dedh = 1.5, dhai = 2.5) is directly visible in them.
2. **NeMo text processing (`hi` and `en` ITN) as an optional, heavier engine** for Devanagari Hindi spans and English spans. Install it in a conda env (Python 3.10, conda-forge pynini) and test that the install succeeds early, because WFST grammar compilation on first run can be slow (not measured here). Post-process the output: map Devanagari digits ०-९ to 0-9, add Indian grouping, and convert US-style phone formatting (123-123-5678) to Indian 10-digit or +91 forms.
3. **`number-parser` (language='hi')** is a pure-Python fallback for Devanagari number words. Test crore and fraction words yourself, since neither is documented.
4. **`WordToNumber`** for Latin-script "two crore fifty lakh". Avoid `text2num` on Python 3.10/Mac (no wheels, no lakh).
- **Code-mixed and romanised input is the main gap.** NeMo `hi` expects Devanagari, so a Latin-script ASR output like "saadhe saat baje" or "dedh lakh rupaye" needs either a romanised lexicon in your rule layer (recommended) or transliteration to Devanagari first (IndicXlit is risky). `hi_en` may help but is undocumented.
- To avoid double-normalising, make sure you know which Sarvam mode produced the input. "transcribe" already normalises numbers; "verbatim" leaves spoken numbers for your normaliser; "codemix" gives Latin English plus Devanagari Hindi, the mixed-script case your normaliser must handle.
- Number->words libraries (num2words EN_IN, indic-num2words) plus Sarvam `spoken_form` can generate round-trip test data (digits -> spoken -> your ITN -> digits).

### Gaps
- I did not research Google Cloud or Microsoft Azure en-IN ITN/formatting behaviour (lakh/crore, "double/triple"). That remains unknown.
- Not verified: whether NeMo hi ITN can emit ASCII digits via a flag, whether it handles "पाव", डबल/ट्रिपल, or romanised Hindi, and what `hi_en` actually expects.
- No open-source tool found for "at the rate", UPI, PAN, IFSC or pincode spoken-form parsing. AI4Bharat IndicTrans and `indic-numtowords` were not examined (they are TN/translation, not ITN).
- I did not check NeMo date ITN test cases for Hindi or Indian-English date order (DD/MM).

## Q4. How does Voice of India's OI-WER handle spelling/script/number variants, and is the scorer open source?

### Takeaway
"OI-WER"/OIWER stands for **Orthographically-Informed WER**, not "Open Indic WER". Each reference word or phrase slot holds a set of accepted variants, and an SCLITE-style DP finds the closest path. Variants cover matras/nukta, loanword spellings, Latin vs native script, compound splits, sandhi, and ITN forms of numbers, dates and currency. Variants are LLM-proposed (Gemini-2.5-Pro) and human-verified. Two MIT-licensed open scorers exist: the official VoI scorer `voi-oiwer` (PyPI; Rust core; macOS wheels) and AI4Bharat's original repo, which also includes the LLM variant-generation scripts. The VoI benchmark data itself is closed.

### Cited Findings
- The OIWER paper (Bhogale et al., arXiv 2603.00941) scores against "a set of permissible spelling variants" per word or subsequence, using SCLITE-style DP. Variant types are matra and diacritic variants (nukta, pulli), loanword spellings, compound split/merge, phonetic variation, ligatures, sandhi, and ITN for numbers, dates, currencies and units. **Gemini-2.5-Pro proposes the variants; human transcribers add or remove them.** LLM-only variants correlate strongly with human-verified ones (R² = 0.89)., [arXiv HTML 2603.00941v1](https://arxiv.org/html/2603.00941v1)
- Reported effects of OIWER:
  - Canary's error rate drops by 6.3 points on average.
  - The Gemini–Canary gap narrows from 18.1 to 11.5 points (Tamil: 17.4 -> 4.3).
  - Substitution errors fall by ~28.5K.
  - OIWER aligns with human-perceived WER 4.9 points better than WER-SN., [arXiv HTML 2603.00941v1](https://arxiv.org/html/2603.00941v1)
- The Josh Talks blog says OI-WER compares output to "a lattice of linguistically valid alternatives"; "If the model's transcription matches any linguistically valid variant, that segment is not penalized". Lattices are "constructed offline, ahead of evaluation, by native-speaking linguists", and no LLM judge is used at scoring time., [Voice of India blog](https://voiceofindiablogs.ai.joshtalks.com/)
  - Its examples: "अमिताभ" / "Amitabh" / "AMITABH" in one slot; "doctor" accepted in Latin or Devanagari; number words, Arabic numerals and Devanagari numerals all accepted ("five hundred"); nukta optional; code-mix variants included.
  - Native speakers approve, prune or extend each lattice., [Voice of India blog](https://voiceofindiablogs.ai.joshtalks.com/)
  - The blog stresses human linguists while the paper describes LLM proposals plus human review. These accounts are consistent: LLM drafts, humans verify.
- **Official scorer: `voi-oiwer`** (`pip install voi_oiwer`):
  - MIT; v0.1.4 (2026-07-13); Python >=3.8; prebuilt wheels for Linux, macOS and Windows (no Rust toolchain needed); one dependency, `indic-nlp-library`.
  - Python handles normalisation via indicnlp (script-specific characters, punctuation stripping, Unicode normalisation); a Rust core does the lattice alignment.
  - API: `oiwer(hypothesis, reference_lists: list[list[str]], input_language="hindi")`. It returns (score %, aligned hyp, aligned ref, ops c/s/d/i, (ins, del, sub), total ref words, metadata, standardized_reference_lists).
  - It covers 24 languages including Hindi, Marathi, Tamil, Telugu, Bengali and Bhojpuri. English is not in the language list.
  - It describes itself as the same implementation that produced the official benchmark results., [PyPI JSON voi-oiwer](https://pypi.org/pypi/voi-oiwer/json); [GitHub JoshTalks/voi_oiwer](https://github.com/JoshTalks/voi_oiwer) (MIT © JoshTalks; public; 0 stars, 13 commits)
- Usage example from the README: `oiwer(hypothesis="नमस्ते दुनिया", reference_lists=[["नमस्ते"], ["दुनिया", "विश्व"]], input_language="hindi")`., [GitHub JoshTalks/voi_oiwer](https://github.com/JoshTalks/voi_oiwer)
- **Original AI4Bharat repo** (MIT; 4 stars, 3 commits): `generate_variations_with_itn.py` (LLM variant generation; needs GCP credentials and project settings), `calculate_oiwer.py`, `oiwer_core.py`, `prompts.py` and `create_variations.sh`. It ships no datasets or lattices., [GitHub AI4Bharat/OIWER](https://github.com/AI4Bharat/OIWER-Orthographically-Informed-Benchmarking-for-ASR)
- The Voice of India benchmark paper (Bhogale et al., arXiv 2604.19151, Interspeech 2026) describes a **closed-source** benchmark of unscripted telephonic conversations: 15 languages, 139 regional clusters, 306,230 utterances, 536 h, and 36,691 speakers., [arXiv 2604.19151](https://arxiv.org/abs/2604.19151)
- The Josh Talks ElevenLabs report gives Scribe v2 OI-WER from 5.9% (Hindi) to 19.6% (Telugu)., [Josh Talks report](https://elevenlabsreport.ai.joshtalks.com/) (from search summary only; not opened)

### Inferences
- For the hackathon eval, use `voi_oiwer`. It is MIT, has a Mac wheel and one light dependency. Hand-build small lattices for the test utterances, with each slot listing the Devanagari and Latin forms of names, digit and word forms of numbers, and ₹/Rs variants. Report OI-WER for raw ASR vs harness output; this matches the methodology judges may know.
- Because OI-WER already forgives script, spelling and number-format variants, a harness that only re-formats numbers or switches script will show **little OI-WER gain**. Real gains come from fixing actual misrecognitions, such as wrong names. Measure entity accuracy (E-WER or contact-hit rate) separately.
- The AI4Bharat `generate_variations_with_itn.py` prompts can be borrowed to auto-draft lattices with any LLM, but they are wired to GCP/Gemini.

### Gaps
- It is unclear how `voi_oiwer` normalises Latin-script tokens (case-folding, English) inside a Hindi lattice, since English is not a listed language. Test it with `standardized_reference_lists`.
- Licence text was confirmed only via the README/sidebar mentions (MIT); I did not read the LICENSE files.
- The VoI test data is not public, so the official benchmark cannot be run locally.
