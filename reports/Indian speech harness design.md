# Shortlist, constrain, then cross-examine every name

The best-evidenced harness is a narrow one, not a clever one. Run Saaras v3 in translit mode (the configuration Equal AI reportedly uses) and gpt-transcribe without keywords in parallel. Normalise both to one script and to digits, and flag only the spans where they disagree or that sound like a contact. Retrieve at most 5–10 phonetically close contacts per flagged span, then let a GPT-4o-class text model pick a replacement only from that shortlist or "keep", under deterministic guardrails. The closest published system, RECOVER, used this shape without training and cut entity-phrase WER by **12–49% relative with overall WER roughly flat**, and by **53% when fusing five commercial ASR vendors** ([RECOVER](https://arxiv.org/html/2603.16411)). Apple's personal-contacts study cut name errors by **74%** using ten or fewer phonetically retrieved candidates ([Apple](https://arxiv.org/html/2409.15353)). The same literature shows what fails. Free-form GPT-4o-mini correction **raised Hindi WER by 11–40%** ([Kumar et al., EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)). Padding a bias list with 250 distractors made speech-LLM biased-word error **39–570% worse** ([Huber & Waibel](https://arxiv.org/html/2608.05759)), and that is the regime gpt-transcribe enters when a 100+ contact list goes into `keywords`. Audio re-listening through gpt-audio is plausible but unproven zero-shot: GPT-4o followed conflicting text 23% of the time even when told to trust the audio ([Billa](https://arxiv.org/abs/2602.11488)). Use it only for leftover sound-alike disputes, with shuffled options and a "none" choice. The proposed cross-examination test has no published precedent. It re-decodes once with the top candidate and once with a sound-alike decoy as the keyword, and commits only names that survive the decoy. It costs one extra $0.0045/min call and is the honest USP: novel, cheap, and untested until your dev set says otherwise. No public benchmark covers personal-context Indian phone speech, so the claim rests entirely on a self-recorded test set split by speaker. Score it for entity accuracy, false insertions and unchanged WER, with paired bootstrap intervals.

## Closed-vocabulary span edits produce the large training-free gains

### Selecting from a shortlist beats rewriting the sentence

The strongest training-free entity results share one move: the LLM may only swap a suspicious span for an entry from a supplied list. RECOVER (Observe.AI, 2026) decodes each segment five ways and retrieves top-K candidates from an entity list. GPT-4o then picks a base hypothesis and proposes entity-only find/replace edits, and each replacement must be exactly one list phrase. A deterministic similarity floor of 0.5 and an LLM critic then accept or reject each edit. Against raw Whisper-large-v3, entity-phrase WER (E-WER) fell **38.5% on Earnings-21, 48.9% on Common Voice, 23.4% on a medical set and 17.5% on noisy air-traffic audio**. Overall WER moved from 12.34 to 12.39, 9.96 to 9.79 and 35.80 to 33.70 ([RECOVER](https://arxiv.org/html/2603.16411)). Fusing one hypothesis each from five commercial vendors did better: **E-WER 7.44 and WER 9.24**, which beats every single vendor except AWS on WER. That is the closest published analogue to fusing Saaras with gpt-transcribe ([RECOVER](https://arxiv.org/html/2603.16411)).

Two details from RECOVER set the harness's priorities. First, gains scale with list coverage: 28.2% relative E-WER reduction at full coverage, but only 8.1% at 25%. A user's own contacts and places are by construction a high-coverage list for the names that user actually says, and that is the structural advantage over any generic model. Second, the corrector must be strong. On noisy ATCO2, GPT-4o-mini kept only 1.57% of the gain against 17.5% for GPT-4o, at $0.84 versus $13.57 per 1,000 segments ([RECOVER](https://arxiv.org/html/2603.16411)).

Designs that retrieve candidates and then select among them confirm the pattern. DeRAGEC retrieves ten phonetically similar named entities, filters them with a multiple-choice "denoising gate", and only then corrects. With GPT-4o-mini it cut WER by **19.5% on Common Voice and 34.8% on STOP**, nearly reaching an oracle that is handed the gold entity ([DeRAGEC](https://arxiv.org/html/2506.07510)). Apple's phonetic-retrieval study used a personal database with hundreds of contacts per user. It detected the entity, retrieved phonetically close contacts, and re-decoded with at most ten of them, cutting name error rate from **37.52 to 9.90**. Simple string replacement without the LLM step did worse (12.60) ([Apple](https://arxiv.org/html/2409.15353)).

The only evidence on Indian proper nouns points the same way. DiP-ASR matched NER-tagged words to a Bollywood/Spotify dictionary by grapheme and phoneme edit distance ≤2, then gave gpt-3.5 the 5-best list plus the dictionary options. WER fell by roughly **8–41% relative** on Hindi, Tamil and Telugu sets, but each set had only 50 utterances. Zero-shot, without the dictionary, the model did worse than baseline on three of six sets ([DiP-ASR](https://aclanthology.org/2024.findings-emnlp.399/)).

Pure selection and token voting are the two tempting shortcuts, and both fall short. Picking one N-best member without editing moved E-WER by only **0.4%** in RECOVER's baselines, because no hypothesis contained the missing entity ([RECOVER](https://arxiv.org/html/2603.16411)). ROVER-style merging inflated WER on noisy ATCO2 from 35.80 to 40.54 through insertions ([RECOVER](https://arxiv.org/html/2603.16411)). It also did worse than the baseline when run over one system's N-best ([Ma et al.](https://arxiv.org/html/2307.04172v2)), and with only two vendors it cannot break ties. The hybrid the evidence supports is to fix a base hypothesis, apply closed-vocabulary span edits, verify, and fall back to the original. Two cheap safeguards help. ProGRes keeps the original hypotheses in the candidate pool so a noisy LLM output can lose to them ([ProGRes](https://arxiv.org/html/2409.00217v2)). Ma et al.'s "closest" mapping snaps LLM output back to the nearest N-best member ([Ma et al.](https://arxiv.org/html/2307.04172v2)).

### Every unconstrained variant fails, and Hindi fails hardest

Over-correction is common, not a corner case. A plain correction prompt to DeepSeek-V2 raised Mandarin CER from **5.06 to 53.10**. Adding error pre-detection, step-by-step localisation and a verify-or-revert step brought it down to 4.69, yet even then 98 correct sentences were broken for 383 fixed ([RLLM-CF](https://arxiv.org/html/2505.24347v3)). Zero-shot ChatGPT made Whisper's TED transcripts about 50% worse, mainly by deleting disfluencies ([Ma et al.](https://arxiv.org/html/2307.04172v2)). RECOVER measured free-form entity-list prompts changing 5.85–7.93% of tokens, against 0.21% for its constrained pipeline ([RECOVER](https://arxiv.org/html/2603.16411)).

The only peer-reviewed Hindi study is the starkest. GPT-4o-mini zero-shot correction pushed IndicConformer from **18.02 to 25.14 WER** and IndicWav2Vec from 28.60 to 31.77. Five similarity-selected examples still left the stronger recogniser worse than raw. The authors name over-editing, stylistic substitution and domain drift as the causes ([Kumar et al., EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)). Saaras v3 and gpt-transcribe are both strong recognisers, which is where unconstrained correction has the most to lose.

Names fail in a specific way: LLMs swap rare names for common ones. DiP-ASR reports the model replacing a correctly transcribed "Preethi" with the more common "Preeti" ([DiP-ASR](https://aclanthology.org/2024.findings-emnlp.399/)), and DeRAGEC attributes rare-entity misses to the same bias toward frequent words ([DeRAGEC](https://arxiv.org/html/2506.07510)).

Candidate lists fail by volume. Handing GPT-4o-mini all ten retrieved entities was *worse* than plain 5-best correction with no candidates (7.1 vs 6.9 WER), because candidate precision falls from 0.137 at K=1 to 0.032 at K=15 ([DeRAGEC](https://arxiv.org/html/2506.07510)). A fine-tuned corrector also got worse going from one hint to five ([Pusateri et al.](https://arxiv.org/html/2409.06062)). RECOVER tolerates K=200 only because candidates are a menu for a closed-vocabulary edit checked by a critic, and even there 769 distractors cost about 2.4 points ([RECOVER](https://arxiv.org/html/2603.16411)).

Numbers fail whatever the method. A fine-tuned Hindi mT5 corrector **broke 17 English-number tokens while fixing 7** ([Kumar et al., EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)).

The mitigations that worked without training translate directly into an output contract. The LLM receives the numbered vendor hypotheses. For each flagged span, and only those, it also gets a short candidate menu with phonetic scores and an explicit KEEP option. (DiP-ASR included the original word among its dictionary options for the same reason.) The LLM returns JSON naming a candidate ID or KEEP for each span, never free text. Code performs the substitution, so words outside entities cannot drift. This span-only contract is what kept non-entity CER unchanged in Generative Annotation NEC ([Generative Annotation NEC](https://arxiv.org/html/2508.20700)).

Code then rejects any edit that:

- is not an exact list entry;
- falls below a phonetic similarity floor;
- lacks a margin over the runner-up; or
- replaces a token that already exactly matches a contact.

That last rule is inferred from the Preethi failure. It makes replacement one-way: into a contact's spelling, never out of one. No published study has tested OpenAI structured outputs for this contract, so treat the JSON-schema mechanism as an engineering choice, not as evidence.

## Pasting the contact list into keywords manufactures false names

### Distractors and sound-alikes are the documented failure of prompt biasing

Bias lists help only while they are short and clean. Huber and Waibel's 2026 comparison found that dedicated biasing modules cut biased-word WER by 37–88% relative when given a clean list. Adding 250 distractors made prompted speech LLMs' biased-word WER **39% to 570% worse**, and words placed early in the prompt fared better. A dynamic-vocabulary method degraded by up to 55% when the true word was absent from the list, mostly through insertions of list tokens ([Huber & Waibel](https://arxiv.org/html/2608.05759)). Other studies put the tipping point at a few hundred entries. CMT-LLM found performance declined past 1,000 words and worsened going from 100 to 400 ([CMT-LLM](https://arxiv.org/html/2506.12059v1)). Apple's name error rate was best at ten candidates and slightly worse at twenty ([Apple](https://arxiv.org/html/2409.15353)). Personal entity lists add a sharper problem: models start mistaking phonetically similar ordinary words for entities ([Xu et al.](https://www.isca-archive.org/interspeech_2023/xu23d_interspeech.pdf)).

The vendor evidence is anecdotal but pointed. AssemblyAI found that adding the variant "Kelly Byrne-Donoghue" made its model mis-transcribe a correctly spoken "Kelly Byrne Donahue" in **3 of 3 runs**, and that a scoped list of about 20 terms beats one of about 800 ([AssemblyAI](https://www.assemblyai.com/blog/when-keyterm-prompting-backfires)). OpenAI itself calls keywords "hints, not required output" and tells developers to check that keywords do not cause "unspoken terms to appear" ([OpenAI STT guide](https://developers.openai.com/api/docs/guides/speech-to-text)). The "distractors" in published studies are unrelated rare words. A contact book full of Rohan/Mohan/Rohit pairs is harder than anything those curves measure.

### What the two APIs actually expose

gpt-transcribe was released on 28 July 2026 at **$0.0045/min**. It is the only OpenAI model that accepts `keywords` and a `languages` array alongside `prompt` ([OpenAI changelog](https://developers.openai.com/api/docs/changelog); [OpenAI pricing](https://developers.openai.com/api/docs/pricing)). It returns neither logprobs nor timestamps. Logprobs come only from gpt-4o-transcribe and gpt-4o-mini-transcribe with `response_format=json`, and word timestamps only from whisper-1 via `verbose_json` ([API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)). Those older models are deprecated but keep running until **26 February 2027** ([OpenAI changelog](https://developers.openai.com/api/docs/changelog)). No limit on the number of keywords is documented. A keyword containing `<`, `>` or a line break gets the whole request rejected. `languages` replaces `language`, so never send both ([OpenAI STT guide](https://developers.openai.com/api/docs/guides/speech-to-text)). An open Vercel AI SDK issue reports `keywords` and `languages` being silently dropped through its provider options, so call the API directly ([vercel/ai #23487](https://github.com/vercel/ai/issues/23487)).

Sarvam's REST endpoint now defaults to `saaras:v4` and labels v3 "legacy". Its only biasing feature, `keyterms`, accepts **at most 50 terms of up to 64 characters, on v4 only**. v3 requests that carry keyterms are rejected, and there is no prompt or context parameter ([Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe); [Sarvam keyterms](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/how-to/keyterms)). It offers five modes:

- transcribe: native script, numbers normalised;
- translate: output in English;
- verbatim: no normalisation;
- translit: everything in Roman script;
- codemix: English in Latin script, Hindi in Devanagari.

Timestamps are chunk-level only, REST clips must be under 30 s, and pay-as-you-go costs **₹0.49/min with a limit of 60 requests per minute**, plus ₹100 of free credit ([Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe); [Sarvam pricing](https://docs.sarvam.ai/api/getting-started/pricing)).

Sarvam's case study says Equal runs **Saaras V3 for about 85% of its speech calls, and 97% of those in translit mode**. It describes no prompts, custom vocabulary, contact context or post-processing ([Sarvam: Equal](https://www.sarvam.ai/stories/equal)). That makes unbiased `saaras:v3` with `mode=translit` the defensible "what Equal runs" baseline. But the lack of a public description is not evidence that Equal has no internal layer, so do not claim it has none.

The fix that works with black-box APIs is to bias late and narrowly. Hitachi's training-free two-pass method first transcribes without biasing while predicting likely term-error spans. It then retrieves phonetic neighbours only for those spans and skips the second pass when nothing is flagged. Queries per utterance fell from 13.37 to 0.99, and biased-term WER fell from **41.43 to 28.05 with unbiased-word WER unchanged** (2.80 to 2.72). Top-10 retrieval beat top-50 ([Hitachi](https://arxiv.org/html/2609.30694)). Huber and Waibel's alternative asks an audio LLM yes or no for each list word. That largely prevented the distractor collapse, but it costs one call per word and ran at just 34.1% precision on Earnings-21 ([Huber & Waibel](https://arxiv.org/html/2608.05759)).

For this harness, native biasing still has a role, but only as a second pass that carries the five or fewer retrieved candidates for a flagged span, never as a standing list. The gpt-transcribe baseline must also be measured both with no keywords and with the full contact list. The full-list setup is what a developer would naturally ship, and it is the one most likely to hallucinate names.

## Re-listening helps only when the audio model cannot see a favourite

### Every positive result was fine-tuned

Two peer-reviewed systems show that turning disagreement into a constrained choice, with the audio available, beats text-only correction. ClozeGER keeps the tokens shared by all N-best hypotheses as fixed context and turns the positions where they differ into blanks with options A–E plus a NULL option. With the speech fed in, Common Voice WER fell from 14.4 to 8.5 ([ClozeGER](https://arxiv.org/html/2405.10025v1)). Prakash et al. encode three systems' disagreements inline as a set of alternatives, which is almost exactly the "disputed span plus candidates" design. On call-centre audio a speech LLM beat a text LLM (**12.92 for the ensemble, 11.39 text, 9.85 speech**), and it avoided the text LLM's regression on clean LibriSpeech ([Prakash et al.](https://arxiv.org/html/2506.11089v1)).

Both systems were fine-tuned with LoRA. Untuned ClozeGER did worse than plain correction. Its main failure was position bias: more than 80% of answers on the WSJ set were option A. Logit calibration over cyclic permutations of the options fixed this, lifting cloze accuracy from 84.7% to 92.6%. Adding speech even hurt on noisy CHiME-4 ([ClozeGER](https://arxiv.org/html/2405.10025v1)).

### Zero-shot audio models defer to text and to option order

The zero-shot evidence is mostly cautionary. Instructed to follow the audio, **GPT-4o followed conflicting text 23.2% of the time and Gemini 2.0 Flash 16.6%**. Framing the text as possibly corrupted cut that rate by 80%, while forcing an explicit transcription first raised it by 14% ([Billa](https://arxiv.org/abs/2602.11488)). Open audio LLMs were worse: text influence exceeded 95%, and their confidence did not drop under adversarial text, so model confidence cannot flag the failure ([When Audio and Text Disagree](https://arxiv.org/html/2508.15407v1)). Shuffling multiple-choice options moved accuracy by up to about 24% for Phi-4-Multimodal and about 5% for Gemini 2.0 Flash, and majority voting over permutations is the recommended fix ([Hearing the Order](https://arxiv.org/html/2510.00628v2)). No paper reports zero-shot GPT-4o-audio or gpt-audio used as a multiple-choice picker over ASR candidates, and none covers Hindi, Hinglish or 8 kHz phone audio.

### Building the verifier on OpenAI's black box

Audio input is available only in Chat Completions, through two models:

- `gpt-audio-1.5`: text at $2.50/$10 and audio at **$32/$64 per million tokens**;
- `gpt-audio-mini`: cheaper, at **$10 per million audio input tokens**.

Audio goes in an `input_audio` part as base64 WAV or MP3. The Responses API does not take audio, and the GPT-5.x reasoning models accept only text and images ([gpt-audio-1.5](https://developers.openai.com/api/docs/models/gpt-audio-1.5); [OpenAI pricing](https://developers.openai.com/api/docs/pricing); [audio chat guide](https://developers.openai.com/api/docs/guides/audio-chat-completions); [OpenAI changelog](https://developers.openai.com/api/docs/changelog)). The reference says `modalities` defaults to text, but every audio example requests `["text","audio"]`. Confirm text-only output in a smoke test, and if it fails, request both and read only the text part ([Chat Completions reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)).

The evidence above dictates how to ask the question:

1. Send the whole short utterance rather than a cropped clip, and do not send the transcript. Give only anchor words ("the name said after 'call'"), mirroring PARDON's two anchor words either side of a span of six words or fewer ([PARDON](https://arxiv.org/html/2610.24809v2)).
2. Offer two to four shortlisted names plus "none of these / unclear", and describe them as guesses from a system that is often wrong.
3. Ask two or three times with the options cyclically permuted, and take the majority.
4. Add a blind arm: the same model transcribes the clip with no candidates, and its output is phonetically matched against the contact list. A model that never saw the options cannot echo them.
5. Commit only when the blind arm and the majority vote agree.

Expect many "none/unclear" answers on phone-band Hinglish. That is the verifier doing its job, and those spans should fall back to the base hypothesis or a read-back in the UI.

### Cross-examination has no precedent, which is both its appeal and its risk

No published work does what the proposed test does: re-transcribe with the leading candidate as the hint, again with a sound-alike decoy, and treat "follows whichever hint it is given" as evidence of echoing. The ingredients are documented, though.

- Alibaba's hotword-retrieval system jointly decodes hypotheses with and without context specifically to suppress hallucinations from irrelevant bias words. It found the top 2 hotwords beat the top 10 (keyword error 11.99 vs 15.21, against 22.63 with none) ([Alibaba](https://arxiv.org/html/2512.21828v1)).
- Microsoft's LOGIC paper reports that speech LLMs "generate entity phrases that are not even spoken" and sometimes recite the prompt list instead of transcribing ("list-vomiting"). It also finds shallow fusion struggles with distractors that sound like the true phrase ([LOGIC](https://arxiv.org/html/2601.15397v1)).
- SALMONN-2 trains on distractor-only lists for utterances that contain none of the listed words, an implicit admission that untrained models echo ([SALMONN-2](https://arxiv.org/pdf/2607.17079)).
- A child-speech study already falls back to the unprompted transcript when the prompted output's length drifts too far ([2506.11079](https://arxiv.org/pdf/2506.11079)).

The black-box version is cheap. gpt-transcribe takes the whole clip, so the name slot can be compared across outputs without any cropping. The test has three arms:

- **Arm 0** is the existing unbiased pass.
- **Arm 1** is the targeted second pass with `keywords=[A]`, where A is the top candidate. The pipeline runs this anyway.
- **Arm 2** is one extra call with `keywords=[B]`. B is the runner-up contact, chosen to be about as phonetically close to the heard span as A is (use the same misheard distance). Keep the wording, list length and position identical.

Read the outcomes like this:

| Outcome | Reading |
|---|---|
| Arm 0 already yields A | The model heard A unaided. |
| Arm 2 still yields A | A survived cross-examination: strong evidence it was heard. |
| Arm 1 yields A and Arm 2 yields B | The model is echoing; the span is unresolved. Escalate to the audio vote or a read-back, and do not count this against A. |

Running the same pair through Saaras v4 `keyterms` costs one more call and adds testimony from an independent vendor. The risks are just as concrete. On genuinely ambiguous phone audio, both arms may echo most of the time, leaving many spans unresolved. If gpt-transcribe largely ignores single keywords, the test tells you nothing, though that would itself show the keywords are weak. Either way, the test produces a number no one has published: **the echo rate of gpt-transcribe keywords on Indian names**, measured on no-name controls and decoy arms. That number is valuable even if the detector disappoints.

## Cross-vendor disagreement is the only black-box error flag, and nobody has calibrated it

Disagreement between complementary recognisers has long been the standard black-box error signal, going back to SRI's premise that "a region where two complementary ASR systems disagree is most likely an error" ([SRI/Tam et al.](https://www.sri.com/publication/speech-natural-language-pubs/asr-error-detection-using-recurrent-neural-network-language-model-and-complementary-asr/)). The largest recent study ran eight systems over 76,398 token positions. 72.1% of positions had near-unanimous agreement and 2.5% were high-risk, and the share of disagreements that were real content errors rose from 53.9% to 73.9% across risk quintiles. But the authors report no precision, recall or AUC against human references, and say the accuracy of flagged regions "remains to be established" ([2604.14152](https://arxiv.org/abs/2604.14152)).

White-box signals are not much better. In PARDON's comparison, Tsallis entropy reached only 4.0% recall at 70% precision on AMI ([PARDON](https://arxiv.org/html/2610.24809v2)). Hitachi's audio LLM predicted error spans at 51.9% precision ([Hitachi](https://arxiv.org/html/2609.30694)). The design consequence: flag for recall and commit for precision. Flag generously, then let retrieval, the constrained selector and the verification arms decide.

The available confidence signals are weaker than they look for Hindi. Logprobs exist only on gpt-4o-transcribe and gpt-4o-mini-transcribe ([API reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)). On Voice of India's Hindi board those models score **32.27 and 17.27 OI-WER**, against 6.94 for GPT Transcribe and 3.69 for Saaras v3 ([Voice of India](https://voiceofindia.ai/stt)). Their text makes a noisy voter, and their logprobs describe the wrong hypothesis. Sarvam exposes no word-level confidence at all ([Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)).

The practical flag set is therefore the union of three cheap signals:

- disagreement between Saaras and gpt-transcribe after normalisation;
- any span within the phonetic read-back threshold of a contact, or matching a call template ("X ko phone karo", "call X");
- every number span.

With two systems, disagreement is a flag, not a vote. ROVER cannot break a two-way tie, and its result depends on the order of the hypotheses ([Jalalvand et al.](https://arxiv.org/pdf/1706.07238)).

Code-mixed text must be put into one script before alignment, or script differences look like acoustic errors. The Hinglish scoring literature does exactly this. MUCS 2021's transliterated WER (T-WER) counts an English word as correct whether it appears in Latin script or in its native-script transliteration. A follow-up system mapped every English word written in Devanagari to Latin in both reference and hypothesis ([MUCS 2021](https://arxiv.org/pdf/2104.00235); [Wiesner et al.](https://www.isca-archive.org/interspeech_2021/wiesner21_interspeech.pdf)). The alignment recipe follows:

1. Romanise every hypothesis (Saaras translit output is already Roman).
2. Convert number words to digits, using the same rules as for the final output.
3. Lowercase and strip punctuation.
4. Run a word-level Levenshtein alignment with a phonetic substitution cost.
5. Merge adjacent mismatches into spans of at most six words, with two anchor words either side.

Cropping the disputed audio is mostly unnecessary, and the options for doing it are poor:

- whisper-1 is the only OpenAI model with word timestamps ([OpenAI STT guide](https://developers.openai.com/api/docs/guides/speech-to-text)).
- Sarvam's timestamps are phrase-level ([Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)).
- The MMS-based `ctc-forced-aligner` needs romanised input, ships a non-commercial default model, and has no published Hindi accuracy ([ctc-forced-aligner](https://www.github.com/MahmoudAshraf97/ctc-forced-aligner)).

Phone commands of a few seconds can go to every verifier whole.

## Names and numbers must stay deterministic

### misheard is the only drop-in cross-script matcher, and it is one week old

`misheard` (formerly `indic-phonetic`) is the only purpose-built, pure-Python, MIT-licensed tool that matches Indian names by sound across Devanagari, Tamil and Roman script. It:

- transliterates Indic script into a phonetic Roman form, applying Hindi schwa deletion;
- folds English-style spellings;
- scores sound substitutions by articulatory features, with a confusion table (v/w, t/ṭ, ph/f);
- makes dropping a silent "a" or an "h" cheap;
- ignores honorifics, and tolerates initials and swapped word order.

`distance("Barmer","बाड़मेर")` is 0.4, while `distance("Mohan","Rohan")` is 1.7 ([misheard](https://github.com/trivedi-aman/misheard)). Its README suggests accepting a match below about 0.8 with at least a 1.0 lead over the runner-up, reading it back to the user below 1.8, and re-asking otherwise. A lookup takes about 5 ms against 780 places ([misheard](https://github.com/trivedi-aman/misheard)).

The caveats are serious. It is alpha with zero stars. Its 100% top-1 benchmark is synthetic and built from the same confusions it models, and it has never been run on real ASR output. PyPI also flags a "change of provenance" on `indic-phonetic` 0.1.1 ([misheard](https://github.com/trivedi-aman/misheard); [PyPI indic-phonetic](https://pypi.org/project/indic-phonetic/)). Read its few kilobytes of source and copy it into the repo rather than installing it.

The fallbacks are well understood:

- **DIY phonetic key (good second opinion).** Use `indic-transliteration` for deterministic Devanagari-to-Roman (MIT, actively released, but no converter for casual spellings), add your own schwa deletion, then score with normalised edit distance ([indic-transliteration](https://github.com/indic-transliteration/indic_transliteration_py)).
- **AI4Bharat IndicXlit (offline only).** It reaches only **52–60% top-1** on Hindi names and drags in fairseq, which breaks on Python 3.11+ ([IndicXlit](https://github.com/AI4Bharat/IndicXlit); [fairseq #5191](https://www.github.com/facebookresearch/fairseq/issues/5191)). Run it once in a separate environment to generate several romanisations per contact, and cache them as aliases.
- **epitran plus PanPhon.** The principled phoneme-level route, but English G2P needs a C build ([epitran](https://github.com/dmort27/epitran)).
- **Symphonym embeddings (skip).** Untested on Indian names, and they let 70.5% of random anagrams through before a fix ([Symphonym](https://arxiv.org/abs/2601.06932)).
- **abydos and jellyfish (avoid).** abydos is GPLv3 and frozen at Python 3.8; jellyfish 1.3.0 needs Python 3.11 ([abydos](https://pypi.org/pypi/abydos/json); [jellyfish](https://pypi.org/pypi/jellyfish/json)).

Do not let an LLM rule on cross-script identity unaided. Qwen2.5-7B's accuracy at recognising the same person fell from **35.1% on Latin-script pairs to 8.5% on Devanagari** ([Same Entity, Different Script](https://arxiv.org/abs/2610.31407)). That is a 7B model and GPT-class behaviour is untested, but the deterministic shortlist costs nothing.

The named-entity correction literature supports phonetic edit distance as the retrieval baseline. Audio-based retrieval beat it substantially only when the written forms differed a lot (NE recall 50.85 vs 86.51), and only on Mandarin with a trained model ([Generative Annotation NEC](https://arxiv.org/html/2508.20700v2)). The scoring recipe:

- Query with the span from every hypothesis, and keep the top five aliases under the read-back threshold.
- Auto-accept only above an absolute threshold plus a margin over the runner-up. An alternative is Apple's rule: normalised phonetic distance under 0.2, or within 1.2× the best ([Apple](https://arxiv.org/html/2409.15353)).

Mohan/Rohan at 1.7 sits just inside misheard's read-back line, so sound-alike pairs correctly reach the selector and the verification arms instead of being auto-accepted. Calibrate thresholds on a synthetic set built from the real contact book before touching real audio. Include true variants such as Sreenidhi/Srinidhi and Mohammed/Muhammad, plus minimal-pair distractors.

One cross-lingual finding applies to the keyword arms. In IndicContextEval, **native-script entity lists helped audio LLMs by up to 11 NEER points more** than English-script lists ([IndicContextEval](https://arxiv.org/html/2606.19157v2)). A/B test whether gpt-transcribe keywords should carry both the Roman and Devanagari forms of each shortlisted name.

### No tool covers Indian spoken formats end to end

NVIDIA's NeMo text processing (Apache-2.0) is the only mature open-source inverse text normalisation (ITN, spoken form to written form) for Hindi. Its Hindi test files cover:

- lakh, crore and arab ("तीन करोड़" → ३०००००००);
- the fraction words ("सवा सात सौ" → ७२५, "डेढ़ सौ" → १५०, "ढाई सौ" → २५०);
- times ("साढ़े पाँच बजे" → ५:३०, "पौने पाँच" → ४:४५);
- money ("ढाई करोड़ रुपए" → ₹२५००००००);
- phone numbers read digit by digit, including +91.

([NeMo cardinal tests](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/hi/data_inverse_text_normalization/test_cases_cardinal.txt); [time](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/hi/data_inverse_text_normalization/test_cases_time.txt); [money](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/hi/data_inverse_text_normalization/test_cases_money.txt); [telephone](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/hi/data_inverse_text_normalization/test_cases_telephone.txt))

Its English grammar handles crore, lakh and "double", but formats phone numbers US-style ([en telephone](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/en/data_inverse_text_normalization/test_cases_telephone.txt)). The catches for this build are large:

- Hindi ITN expects Devanagari input and emits Devanagari digits without grouping.
- pip installs on macOS are unsupported because of Pynini; it installs only through conda-forge.
- No tests cover "triple", "at the rate", UPI handles, PAN, IFSC or pincodes.

([NeMo](https://github.com/NVIDIA/NeMo-text-processing); [en electronic](https://raw.githubusercontent.com/NVIDIA/NeMo-text-processing/main/tests/nemo_text_processing/en/data_inverse_text_normalization/test_cases_electronic.txt))

Lighter libraries fill only corners. `number-parser` parses Devanagari lakh but documents no crore ([number-parser](https://pypi.org/pypi/number-parser/json)). The `WordToNumber` fork handles Latin-script "two crore fifty lakh" ([WordToNumber](https://pypi.org/project/WordToNumber/)). `text2num` has no Hindi and no Mac wheels for Python 3.10 ([text2num](https://pypi.org/pypi/text2num/json)).

Saaras complicates things further, because its mode decides who normalises. Transcribe mode already normalises numbers and verbatim mode leaves spoken numbers intact. Translit mode, Equal's mode, emits romanised text that no open ITN accepts ([Sarvam API reference](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)). The right answer for 28 hours is a small deterministic rule layer over romanised Hinglish and English:

- a lexicon from ek through sau, hazaar, lakh and crore;
- the fraction words saadhe (+½), sava (+¼), paune (−¼), dedh (1½) and dhai (2½), applied to units and to "baje";
- "double/triple X" expansion before digits are joined;
- "at the rate" and "dot" mapped to @ and . inside email or UPI contexts;
- Indian digit grouping for ₹ amounts;
- 10-digit and +91 phone normalisation;
- format validators for PAN, IFSC and pincode.

Copy NeMo's Hindi test cases, romanised, as the unit-test spec. Generate round-trip test variants with an EN_IN number-to-words library or Sarvam's `spoken_form` ([Sarvam transliterate](https://docs.sarvam.ai/api-reference-docs/text/transliterate)).

The LLM never edits digits. When vendors disagree on a digit string, the alternatives go to the audio vote or a read-back. OpenAI's gpt-realtime-2.1 claims "improved alphanumeric recognition" and could give an extra opinion, but this is untested ([OpenAI changelog](https://developers.openai.com/api/docs/changelog)). Because OI-WER already forgives variants in number format and script, number fixes will barely move it. They have to be reported as entity accuracy ([OIWER paper](https://arxiv.org/html/2603.00941v1)).

## No one has published this harness, so the evaluation is the claim

### The nearest work is a benchmark, a weekend study and an English paper

No public project combines commercial ASR APIs, personal contact context, Indian phone audio, Hinglish and fusion of several vendors. The closest benchmark is AI4Bharat's **IndicContextEval** (Interspeech 2026; CC BY 4.0). It has 56 hours across eight languages and a seven-level prompt ladder, running from no context up to 20–30-entity lists in English or native script, plus an adversarial list from an unrelated domain ([IndicContextEval README](https://raw.githubusercontent.com/AI4Bharat/IndicContextEval/main/README.md)). Its numbers frame the opportunity. With language-only context, named-entity error rate (NEER) was **35.59 for GPT-4o Transcribe and 25.93 for Sarvam Audio**. Sarvam Audio was "largely insensitive to context", and GPT-4o-class models moved by less than a point under wrong-domain lists ([IndicContextEval](https://arxiv.org/html/2606.19157v2)).

The closest study to the harness idea is a one-person benchmark. It ran Claude Haiku post-correction, with a strict glossary-only prompt, over Saaras v3 on 50 clean read clips. Term recall rose from **92.7% to 95.8%**: a real gain, but small headroom, on easy audio, and without vendor biasing enabled ([asr_bench_med50](https://blog.gopenai.com/contextual-biasing-vs-generative-error-correction-for-indic-languages-836e66951f6b)). RECOVER remains English-only, AgenticASR publishes no numbers, and CLEAR's repo has no instructions ([AgenticASR](https://github.com/InteractiveASR/AgenticASR); [CLEAR](https://github.com/flamenlp/CLEAR)). Sarvam's open `llm_intent_entity` scorer offers an Entity Preservation Score covering names, places, dates and quantities ([Sarvam](https://www.sarvam.ai/blogs/evaluating-indian-language-asr)).

### Vendors all sell biasing, none publish Indian phone entity accuracy

Every major vendor now offers a keyword list. Limits include Deepgram up to 100 terms, ElevenLabs Scribe v2 up to 1,000 in batch, AssemblyAI up to 1,000 and Gnani Prisma v3.0 up to 200. Published entity numbers on Indian speech are vendor-reported and on read speech only. An example is Gnani's rise from 70.9% to 90.3% recall of supplied terms, which Gnani itself calls an upper bound ([Deepgram](https://developers.deepgram.com/docs/keyterm); [ElevenLabs](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/keyterm-prompting); [Gnani via AIM](https://analyticsindiamag.com/ai-news/gnani-ai-launches-prisma-v30-speech-recognition-model-for-10-languages)). Smallest.ai warns that boost intensities above 10 increase "the chance of hallucinating the keyword when it was not spoken" ([Smallest](https://docs.smallest.ai/models/documentation/speech-to-text-pulse/features/keyword-boosting)). Nobody publishes a false-positive rate on Indian speech, and that is the gap the harness can fill.

On general Hindi telephone transcription, the Voice of India leaderboard puts **Saaras v3 second at 3.69% OI-WER and GPT Transcribe sixteenth at 6.94%**, behind the open-source Bodhan Indic Transcribe Core at 3.39%. Models run with default settings and "no per-model prompt engineering, custom vocabulary or biasing lists". The test set is closed, there is no Hinglish category, and there are no confidence intervals ([Voice of India](https://voiceofindia.ai/stt); [methodology](https://voiceofindia.ai/methodology)). Two conclusions follow. Saaras v3 should supply the base text for everything that is not a flagged entity. And the harness's results measure something different from the leaderboard, so never present them as a leaderboard comparison.

### A credible protocol in one day

Public data cannot carry the main claim, because no Indian telephone set labelled with named entities exists. The usable public sets are:

- **IndicContextEval Hindi split:** 3,110 utterances, 9.08 h, with entity and adversarial lists for each utterance ([IndicContextEval HF](https://huggingface.co/datasets/ai4bharat/IndicContextEval)).
- **Lahaja:** 12.5 h of Hindi, heavy in entities, gated ([Lahaja](https://huggingface.co/datasets/ai4bharat/Lahaja)).
- **Svarah:** Indian-accented English including payment scenarios, gated ([Svarah](https://huggingface.co/datasets/ai4bharat/Svarah)).
- **Gramvaani SLR118:** real, noisy Hindi phone speech, about 61% at 8 kHz, academic use only ([Gramvaani](https://openslr.org/118/)).
- **MUCS 2021 SLR104:** Hindi-English code-switched lectures ([MUCS](https://openslr.org/104/)).

The primary set has to be self-recorded over a real phone path against a real contact book, and scored on these systems:

| System | Configuration | What it answers |
|---|---|---|
| A. Saaras v3 raw | `saaras:v3`, `mode=translit`, no biasing | The baseline matching what Equal runs |
| B. gpt-transcribe raw | `languages=["hi","en"]`, no keywords | OpenAI floor |
| C. gpt-transcribe + full keywords | Every contact and place in `keywords` | Native biasing as a developer would ship it |
| D. gpt-transcribe + shortlist | Harness retrieval feeding five or fewer keywords, nothing else | Whether retrieval alone explains the gain |
| E. Saaras v4 + keyterms | Shortlisted terms, 50 or fewer | Pre-empts "you ignored Sarvam's biasing" |
| F. Harness | Full pipeline | The claim |
| F ablations | Without cross-examination; without the audio vote | Which stages earn their latency |

Score these metrics:

- **Entity accuracy (primary).** Use named-entity error rate or entity recall on names and numbers. Count a name correct on an exact match after mapping to its canonical spelling, or on a fuzzy match. Count a number correct only after digit normalisation ([IndicContextEval](https://arxiv.org/html/2606.19157v2); [RECOVER](https://arxiv.org/abs/2603.16411)).
- **Collateral damage.** Report WER on non-entity words and overall OI-WER alongside it. `voi_oiwer` is the scorer Voice of India uses, is MIT-licensed and has Mac wheels ([voi-oiwer](https://pypi.org/pypi/voi-oiwer/json)). English is not in its language list, so test how it handles Roman-script Hinglish before relying on it.
- **False-insertion rate.** Count contact names that appear where none was spoken. Report it separately on no-name controls, on utterances naming someone outside the contact book, and on utterances whose true name has a sound-alike in the book. This mirrors IndicContextEval's adversarial level and AssemblyAI's homophone case. AssemblyAI's warning that "hit rate always improves, so it hides regressions" is why this metric is needed ([AssemblyAI](https://www.assemblyai.com/blog/when-keyterm-prompting-backfires)).
- **Statistics.** Compute paired bootstrap intervals over utterances, blocked by speaker, because correlated utterances make plain intervals "much narrower than what they should be" ([Bisani & Ney](https://www-i6.informatik.rwth-aachen.de/~bisani/bootlog.html); [block bootstrap](https://ar5iv.arxiv.org/html/1912.09508)).

Split by speaker into a dev set, used for every prompt and threshold decision, and a test set scored once. With 30–100 utterances the intervals will be wide; say so on the slide. Finally, run the frozen harness on a slice of IndicContextEval Hindi. Use its entity lists as context and its adversarial lists as a false-insertion stress test, to show the method is not tuned to your own voice.

## Conclusion: ship the narrow harness, brand the cross-examination

The research reframes the problem. The entity gain does not come from a smarter language model. It comes from a closed, personal list with high coverage, and from refusing the model any edit that is not on that list. Native keyword biasing is less a competitor than an adversary to measure. With a full contact book it enters exactly the distractor regime that makes speech LLMs insert names, and nobody has published how often that happens on Indian speech. Saaras v3 already leaves little general WER to win, so a measured false-insertion rate makes a stronger demo than any WER delta. The cross-examination test turns that weakness into an instrument.

### Ranked pipeline

| # | Stage | API / tool | Evidence behind it | Rank |
|---|---|---|---|---|
| 1 | Context index: each contact and place gets a canonical Roman form plus aliases (Devanagari, spelling variants) | Vendored `misheard` `Matcher` with (key, text) aliases; `indic-transliteration`; IndicXlit top-k run once offline in a separate venv, cached as JSON | DiP-ASR dictionary; misheard; IndicXlit's 52–60% top-1 means use it only for recall | Core |
| 2 | First pass, unbiased, in parallel | Saaras v3 `mode=translit` (base text, matches Equal); gpt-transcribe `languages=["hi","en"]`, no keywords; optionally Saaras v4 translit as a third voice | RECOVER: vendor diversity; Hitachi: unbiased pass 1; Voice of India: Saaras strongest on Hindi | Core |
| 3 | Normalise for comparison only | Romanise, lowercase, strip punctuation, number words to digits via the stage-9 rules | Ma et al.: formatting creates fake diversity; T-WER practice | Core |
| 4 | Align and flag | Word-level Levenshtein with phonetic cost. Flag disagreement, contact near-matches under the read-back threshold, call templates and number spans; spans of six words or fewer plus anchors. No flags means the text passes through untouched | 2604.14152; PARDON; Hitachi skip rule | Core |
| 5 | Retrieve a shortlist per span | misheard distance over all aliases × every hypothesis's version of the span; top 5 (never more than 10); absolute threshold plus margin | Apple ≤10; DeRAGEC precision collapse; misheard thresholds | Core |
| 6 | Targeted biased re-decode, fed in as an extra hypothesis | gpt-transcribe `keywords` = shortlist (5 or fewer); optionally Saaras v4 `keyterms` with the same shortlist | Hitachi: B-WER 41.43→28.05 with U-WER flat; Alibaba: top-2 best | Strong |
| 7 | Constrained select | GPT-4o-class or stronger OpenAI text model; JSON schema per span {candidate_id \| vendor_alt \| KEEP}; code applies edits; guardrails (exact-contact lock, phonetic floor, margin, no edits outside spans, digits excluded); falls back to base | RECOVER (0.21% of tokens touched); DeRAGEC multiple-choice gate; span-only output; RLLM-CF revert | Core |
| 8a | Cross-examination of sound-alike disputes | One extra gpt-transcribe call with `keywords=[decoy]`; commit only if the name survives | No precedent; Alibaba joint decoding; LOGIC | USP (untested) |
| 8b | Audio vote on what remains | `gpt-audio-mini` or `gpt-audio-1.5` via Chat Completions; whole clip, no transcript, options shuffled 2–3 times, "may be wrong" framing, "none" option, plus a blind transcription arm | Billa; Hearing the Order; ClozeGER | Stretch |
| 9 | Deterministic number and format ITN | Own rule layer (romanised lexicon, double/triple, lakh/crore, fraction words, +91, ₹ grouping, @ for "at the rate", UPI, PAN/IFSC/pincode validators), with NeMo Hindi tests as the spec | NeMo coverage and its gaps; EACL number breakage | Core |
| 10 | Output with an evidence trail | Roman-script transcript in the contact's canonical spelling, plus a verdict for each entity (agreed / selected / survived decoy / unresolved → read-back) | OpenAI: "checking the results against the audio" | Core (demo) |

Stages 1–5, 7, 9 and 10 carry nearly all of the gain the evidence supports, and they should work end to end before anything else is attempted. Stage 6 comes next: it is cheap, it has the cleanest published result on unbiased-word WER (U-WER), and it is also arm 1 of the cross-examination. Stage 8a adds one call per disputed span. Stage 8b comes last because its zero-shot reliability is the least supported.

### The USP: context that must survive cross-examination

Brand the framework around the idea that **personal context is only allowed to change a transcript when the change survives a decoy**. Be precise about which parts are novel. Retrieving from a personal list followed by constrained selection is established practice (RECOVER, Apple, DeRAGEC), so present it as a faithful, well-guarded implementation, not an invention. What is new is three things:

- using a sound-alike decoy hint as a black-box test of whether a recogniser heard a name or merely echoed the hint;
- committing names only when they show that invariance;
- publishing the echo rate and false-insertion rate that no vendor reports for Indian speech.

All of this is untested. It may leave many spans unresolved on noisy phone audio, and if gpt-transcribe largely ignores single keywords it will tell you nothing. The dev set must show three things before the slide claims it works:

- the measured echo rate of gpt-transcribe keywords on Rohan/Mohan-type pairs;
- the precision of names committed after surviving the decoy, against names committed by the selector alone;
- the harness's false-insertion rate against system C.

If cross-examination does not raise precision on dev, keep it in the demo as a measurement tool and say plainly that it did not help as a filter. That is still a result nobody else has.

### Expected gains

| Source | Setting | Reported effect | Caveat for this harness |
|---|---|---|---|
| [RECOVER](https://arxiv.org/html/2603.16411) LLM-Select, GPT-4o | 5 Whisper samples, English domains | E-WER −12.8% to −48.9% relative; WER roughly flat | English only; gain drops to 8% at 25% list coverage |
| [RECOVER](https://arxiv.org/html/2603.16411) 5-vendor fusion | Earnings-21 | E-WER 15.88 → 7.44; WER 9.24 | Five vendors, not two |
| [Apple](https://arxiv.org/html/2409.15353) phonetic retrieval | Contacts, hundreds per user | Name error 37.52 → 9.90 | English assistant; not tested on commercial APIs |
| [Hitachi](https://arxiv.org/html/2609.30694) two-pass | Medical, Qwen3-Omni | B-WER 41.43 → 28.05; U-WER 2.80 → 2.72 | Open-weight audio LLM, not an API |
| [DeRAGEC](https://arxiv.org/html/2506.07510) | Common Voice / STOP, GPT-4o-mini | WER −19.5% / −34.8% | English |
| [DiP-ASR](https://aclanthology.org/2024.findings-emnlp.399/) | Indian proper nouns, gpt-3.5 | WER −8% to −41% (computed) | 50-utterance sets; zero-shot was worse on 3 of 6 |
| [asr_bench_med50](https://blog.gopenai.com/contextual-biasing-vs-generative-error-correction-for-indic-languages-836e66951f6b) | Saaras v3 + Claude Haiku, clean read speech | Term recall 92.7% → 95.8% | Little headroom; tiny set |
| [Kumar et al.](https://aclanthology.org/2026.eacl-short.45.pdf) | Free-form GPT-4o-mini on Hindi | WER +11% to +40% (worse) | The failure mode to design out |

My working expectation is an inference from these brackets, not a measured result. On a self-recorded phone set heavy in contact names, where the baselines miss a meaningful share of names, I expect three things:

- relative entity-error reduction against the better baseline in the lower half of RECOVER's 12–49% band;
- overall WER and OI-WER within noise of the Saaras v3 base, because edits are confined to flagged spans;
- a clearly lower false-insertion rate than gpt-transcribe with the full keyword list.

By design the harness should gain nothing on ordinary words. Three conditions shrink the gain:

- **Baseline already near ceiling.** If the baselines already get about 93% of names, as Saaras v3 did on clean read speech, absolute headroom is a few points.
- **Names missing from every hypothesis.** Text-only correction "has little signal to recover" them ([RECOVER](https://arxiv.org/abs/2603.16411)), so those cases depend on stage 6 and the audio arms.
- **Names outside the contact book.** These cannot be fixed at all, and must only be protected from false replacement.

On cost and latency: RECOVER's GPT-4o configuration averaged about two LLM calls per segment at $13.57 per 1,000 segments ([RECOVER](https://arxiv.org/html/2603.16411)). ASR passes cost $0.0045/min on OpenAI and ₹0.49/min on Sarvam. A single GPT-4o-mini correction took about 2 s per Hindi utterance ([Kumar et al.](https://aclanthology.org/2026.eacl-short.45.pdf)). The full harness therefore suits post-call processing or flagged turns, not live streaming.

### What to avoid

| Avoid | Why |
|---|---|
| A free-form "fix this Hinglish transcript" pass | Raised Hindi WER by 11–40% ([Kumar et al.](https://aclanthology.org/2026.eacl-short.45.pdf)); a plain prompt took CER from 5.06 to 53.10 ([RLLM-CF](https://arxiv.org/html/2505.24347v3)) |
| The full contact list in `keywords` or `keyterms` "just in case" | Distractor collapse ([Huber & Waibel](https://arxiv.org/html/2608.05759)); sound-alike overrides ([AssemblyAI](https://www.assemblyai.com/blog/when-keyterm-prompting-backfires)); Sarvam caps keyterms at 50 |
| Letting the LLM touch digits | Even a fine-tuned corrector broke 17 English numbers for every 7 it fixed ([Kumar et al.](https://aclanthology.org/2026.eacl-short.45.pdf)) |
| Letting the LLM decide cross-script identity alone | Same-person accuracy fell from 35.1% to 8.5% on Devanagari ([2610.31407](https://arxiv.org/abs/2610.31407)) |
| GPT-4o-mini as the corrector | Kept 1.57% vs 17.5% of the gain on noisy audio ([RECOVER](https://arxiv.org/html/2603.16411)) |
| More than about ten free-text candidates per span | Ten unfiltered candidates did worse than none ([DeRAGEC](https://arxiv.org/html/2506.07510)) |
| ROVER voting with two or three systems | Cannot break ties; inflated WER on noisy audio ([RECOVER](https://arxiv.org/html/2603.16411)) |
| Showing the transcript to the audio model, asking it to transcribe then choose, or using a fixed option order | Forced transcription raised text dominance by 14% ([Billa](https://arxiv.org/abs/2602.11488)); option order swings accuracy by up to 24% ([Hearing the Order](https://arxiv.org/html/2510.00628v2)) |
| gpt-4o-transcribe as a voter on Hindi | 32.27 OI-WER on Voice of India ([VoI](https://voiceofindia.ai/stt)) |
| Cropping on Sarvam timestamps | Phrase-level only ([Sarvam](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)) |
| IndicXlit/fairseq or pip-installed NeMo in the main Mac environment | fairseq breaks on Python 3.11+; Pynini needs conda-forge ([IndicXlit](https://github.com/AI4Bharat/IndicXlit); [NeMo](https://github.com/NVIDIA/NeMo-text-processing)) |
| Unpinned `misheard`, abydos, jellyfish 1.3 on Python 3.10 | Provenance flag; GPL and Python 3.8 ceiling; needs 3.11 ([PyPI](https://pypi.org/project/indic-phonetic/)) |
| The Vercel AI SDK path for keywords; keywords containing `<`, `>` or newlines; sending `language` and `languages` together | Keywords silently dropped ([#23487](https://github.com/vercel/ai/issues/23487)); requests rejected ([OpenAI](https://developers.openai.com/api/docs/guides/speech-to-text)) |
| Reporting keyword hit rate alone | "Hit rate always improves, so it hides regressions" ([AssemblyAI](https://www.assemblyai.com/blog/when-keyterm-prompting-backfires)) |
| Tuning on the test split, quoting Voice of India ranks as if comparable, or claiming Equal has no context layer | Leaderboard uses default settings and closed data ([VoI methodology](https://voiceofindia.ai/methodology)); Equal's pipeline is undisclosed ([Sarvam: Equal](https://www.sarvam.ai/stories/equal)) |

### Build order to the Sunday 14:00 code freeze

It is 13:08 IST on Saturday 21 November, leaving about 25 hours including sleep.

| Window (IST) | Block | Exit criterion |
|---|---|---|
| Sat 13:15–14:30 | Smoke-test every call. Build a disk cache keyed by audio hash, model and parameters | One cached response each from: gpt-transcribe with `keywords[]` and `languages[]`; Saaras v3 translit; Saaras v4 codemix with keyterms; gpt-audio returning text only; gpt-4o-mini-transcribe logprobs; whisper-1 word timestamps |
| Sat 14:30–17:30 | Build the contact book: at least 100 entries with deliberate sound-alike pairs, plus places, in Roman and Devanagari. Record 60–100 utterances over a real phone call with three or more speakers, covering: names in the book; names not in it; no-name controls (about 20%); phone numbers with double/triple; ₹ lakh/crore; times with saadhe/sava; UPI IDs; Hinglish. Write references. Split by speaker | Test folder frozen and not looked at |
| Sat 17:30–19:30 | Run systems A–E on all audio (cached; throttle Sarvam to 60 RPM). Write the scorer: entity accuracy, false insertions, U-WER, OI-WER, paired bootstrap. Start the IndicContextEval Hindi download | Dev baseline table |
| Sat 19:30–22:30 | Build the context index (vendored misheard, aliases, DIY key) and check retrieval recall@5 on dev name spans. Build the number rule layer, with romanised NeMo cases as tests | Recall@5 high on dev; number tests pass |
| Sat 22:30–01:30 | Normalise, align and flag. Build the constrained JSON selector with KEEP, guardrails and the exact-contact lock; unflagged text passes through | Harness beats the best baseline on dev entity accuracy with U-WER unchanged. If U-WER rises, tighten guardrails before sleeping |
| 01:30–07:00 | Sleep, with IndicContextEval baselines running in the background |, |
| Sun 07:00–10:00 | Add the shortlist re-decode (stage 6), the cross-examination decoy arm, and the audio vote with blind arm. Ablate each on dev | Keep only arms that raise precision on committed entities; record the echo rate |
| Sun 10:00–11:00 | Freeze config and thresholds. Run the test set once, compute bootstrap CIs, and run the frozen harness on the IndicContextEval slice | Final numbers |
| Sun 11:00–13:15 | Build the demo: an evidence trail for each utterance (hypotheses, flags, candidates, arm verdicts). Slides: ablation table, false-insertion chart, echo rate. README with honest caveats | Demo runs from cache |
| Sun 13:15–14:00 | Buffer and code freeze | Tagged build |

If you are behind at 01:30, cut in this order:

1. the audio vote (8b);
2. the IndicContextEval run;
3. the Saaras v4 second opinion.

Keep the cross-examination arm, because it costs one call and reuses stage 6. Never cut the no-name and sound-alike controls or the frozen test split. Without them, the claim to beat Saaras v3 and gpt-transcribe with keywords cannot be checked.
