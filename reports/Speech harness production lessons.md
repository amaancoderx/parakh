# Harden Parakh's verifier, then prove it

Parakh does not need new modelling in its last 20 hours. It needs the guardrails, evidence discipline and plumbing that non-English production systems built around a core Parakh already has. Chinese, Japanese and Korean hotword systems settled on the same design: an unbiased first pass; hint lists of one to three names (a prompt-style recogniser's error rate rose ninefold, **from 3.24 to 29.42, at fifty hints** ([H-PRM](https://arxiv.org/html/2508.18295v1))); verification against unbiased output ([VISH](https://arxiv.org/abs/2610.27867)); and an explicit option to write nothing ([SeACo-Paraformer](https://arxiv.org/html/2308.03266v4)). Those systems also add vetoes that Parakh lacks. They cancel partial matches, reject hinted runs that disturb other words, and distrust short names and names that are also common words. Arabic and African shared tasks add two more lessons. Fusion pays only when the witnesses are independent, so Saaras v3 agreeing with Saaras v4 should not count as corroboration. And LLM correction hurts strong recognisers and numbers ([Intron](https://arxiv.org/html/2501.15310v1)). Dragon, Alexa and Gboard learn only from confirmed corrections or behind thresholds, so Parakh's automatic name memory needs a "candidate" tier and a "verified" tier.

The evaluation is the weakest link. With 140 mentions the study can reliably detect only gains of roughly 6–11 points. The **+5.7-point lead over keyword-biased gpt-transcribe (CI +0.7 to +11.7)** therefore needs at least 300 mentions to stand up. The sharper differentiator is under-measured: on IndicContextEval, Parakh wrote **1 list name that was never spoken, against 16 for keyword biasing**.

The production version is a thin asynchronous API: upload, job, then result with evidence for every edit. It runs on ECS Express in Mumbai, because App Runner is closed to new customers ([AWS](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)). Sarvam retention is set to zero and audio is deleted after a day. Vendor speech recognition costs about **₹1.5 (US$0.017) per audio minute**, or ₹1.1–1.2 if Saaras v3 runs only when the other recognisers disagree. The build order:

- **Tonight:** freeze the test split and build the vetoes.
- **Before sleep:** the service and the memory tiers.
- **Morning:** deployment and the UI.
- **Before the 2 PM freeze:** score the frozen test set exactly once.

## East Asian hotword systems settled on Parakh's design, then added vetoes

**The shared core.** The best-documented Chinese, Japanese and Korean contextual-biasing systems reached the design Parakh built independently. Alibaba's SeACo-Paraformer scores the whole hotword list once, keeps only the top 50 and decodes again with that shortlist. It also has an explicit "no-bias" output that hands the decision back to the plain recogniser. On industrial test sets it raised full-hotword recall **from 12% unbiased to 65%** ([SeACo-Paraformer](https://arxiv.org/html/2308.03266v4)).

H-PRM, a pre-retrieval module built for SeACo, matched hotwords against the *recognised text* in phoneme space. That beat both audio-to-audio and text-to-text matching, and it is what Parakh's phonetic key does over three transcripts. Its sharpest result concerns prompt-style recognisers like gpt-transcribe. Whisper-small did best with about three hints, and Qwen2-Audio with one: its mixed error rate rose **from 3.24 to 29.42 at fifty hints**. Some of the paper's in-text numbers disagree with its tables ([H-PRM](https://arxiv.org/html/2508.18295v1)).

The strongest Chinese correctors also retrieve very few candidates: k = 3 in RASTAR, k = 10 in DANCER and JSPG. JSPG takes the best local alignment across every hypothesis in the N-best list, which is the counterpart of treating Parakh's three recognisers as an N-best list ([RASTAR](https://arxiv.org/abs/2602.12287); [JSPG](https://arxiv.org/html/2605.16896v1)).

The closest published analogue to cross-examination is VISH, an October 2026 preprint. It checks each candidate against a frozen, unbiased CTC model, then prompts a black-box recogniser with only the survivors. On AISHELL-1-NE it took Whisper-medium's biased-word CER **from 21.3 to 7.6, against 7.4 with oracle hotwords** ([VISH](https://arxiv.org/abs/2610.27867)). Parakh uses the no-hint transcripts as its unbiased witness instead of a local model, which keeps it API-only.

**The vetoes.** What separates these systems from naive biasing is a set of vetoes, and Parakh lacks several.

- **Partial matches lose their credit.** The k2/sherpa-onnx, WeNet and icefall context graphs give hotword credit token by token. If the phrase never completes, they **take the whole bonus back**, so a name's first syllables cannot pull an ordinary word towards it. WeNet also matches only one hotword at a time ([sherpa-onnx](https://k2-fsa.github.io/sherpa/onnx/hotwords/index.html); [WeNet](https://wenet-e2e.github.io/wenet/context.html)).
- **Whole keywords only, and no one-syllable boosts.** Naver's CLOVA Speech applies a boost only when the whole keyword is recognised. It tolerates trailing particles (홍길동님) but not fragments (길동님), and ignores spacing. It **refuses one-syllable boosts outright** and recommends at most 500 keywords, because similar keywords confuse each other ([CLOVA Speech](https://api.ncloud-docs.com/docs/ai-application-service-clovaspeech-longsentence)).
- **Short and common-sounding terms are risky.** Mitsubishi Electric's Japanese study found biasing raised keyword insertions **from 1.6% to as much as 12.0%**, and its gains held only for keywords of five or more morae ([MERL](https://merl.com/publications/docs/TR2024-073.pdf)). Alibaba tells customers to give terms that sound like common words its weakest weights ([Alibaba Model Studio](https://help.aliyun.com/zh/model-studio/improve-asr-accuracy)).

Translated to Hinglish, these become five rules:

1. A hinted name counts only if the complete name appears, aligned to the disputed span. A prefix ("Rajes" for "Rajesh Kumar") or a name merged with neighbouring words reverts.
2. Matching strips the postpositions -ji, ne, ko, se, ka/ki/ke and wala, and treats "Ram Prasad" and "Ramprasad" as the same.
3. Names that are also ordinary words need stronger evidence: Pooja/puja (worship), Kamal (lotus), Suraj (sun), Asha (hope). So do very short names such as Om and Raj.
4. One disputed span per cross-examination call, following WeNet's one-hotword rule.
5. A hinted re-run that changed words outside the disputed span is itself suspect. VISH reports that long candidate lists cause "bias-driven substitutions in both hotwords and background words".

**Thresholds and homophones.** A Japanese name corrector from Honda Research Institute and Tokyo Tech compared reading keys and replaced a name only above a similarity threshold. **Always replacing gave 27.6 CER-NE, exact-match-only gave 28.6, and the tuned middle threshold of 0.5 gave 19.8** ([Sudo et al.](https://www.isca-archive.org/interspeech_2023/sudo23b_interspeech.pdf)). Parakh's thresholds should likewise be swept on a dev split, not set by hand.

DANCER shows the trap in pure phonetic retrieval. On a homophone-heavy Mandarin set, pinyin edit-distance correction **made entity errors worse, from 15.58 to 20.88 NE-CER**, until a semantic tie-breaker was added. Its N-best rejection test discards a correction that sits farther from the recognisers' hypotheses than the original span did. With the test, non-entity CER stayed at 4.00; without it, it rose to 4.64 ([DANCER](https://arxiv.org/abs/2403.17645)).

Parakh's rule of writing only where no other recogniser backs the base text is a coarse version of that test, and it should be made explicit. Its vote over hint orders, with abstention, is a safer homophone breaker than a semantic prior. A prior drawn from memory or discovery could manufacture the wrong Rohan out of a Mohan. Memory frequency should therefore only set the order of the alternatives shown to the user, never decide.

**Precedents for Parakh's unusual choices.** Two of them have partial precedents.

- **LLM-written pronunciations.** Hitachi found that an LLM's simplified pronunciation, written in a kana-like form close to the native script, was the best phonetic notation for a rare-word corrector: rare-word recall rose **from 44.5 to 82.0**. IPA caused over-correction and pushed CER to 27.3 ([Hitachi](https://arxiv.org/html/2505.17410v1)). Parakh's pronunciations should stay simple romanised Hindi, never IPA.
- **The vote over three hint orders.** This has no Chinese, Japanese or Korean precedent; the nearest evidence is indirect. Shuffling multiple-choice options changed audio-LLM accuracy by up to about 24%, and voting across orderings is the recommended fix ([Hearing the Order](https://arxiv.org/html/2510.00628v2)). Speech LLMs favour words placed early in a prompt ([Huber & Waibel](https://arxiv.org/html/2608.05759)). Shuffled-word prompts worked as well as ordered ones for Arabic Whisper prompting ([Talafha et al.](https://arxiv.org/html/2511.18774)). The order vote is well motivated but unvalidated, so its echo rate is a number worth measuring and publishing rather than assuming.

One more experiment is worth an hour: which script each hint is written in. Mitsubishi found that choosing each keyword's script individually beat one global choice by **0.09–0.12 keyword F1**. IndicContextEval found that native-script entity lists helped audio LLMs by up to 11 named-entity error rate (NEER) points more than English-script lists ([IndicContextEval](https://arxiv.org/html/2606.19157v2)).

## Arabic, African and code-switched pipelines fuse whole calls and keep the LLM out of the text

**Don't route audio by language.** The Arabic and code-switching literature nearly all agrees that the fragile step is splitting audio by language or dialect and routing each piece to a specialist recogniser:

- At NADI 2026, a learned router recovered **only 44% of the gain that perfect (oracle) routing would give** ([Itgan, NADI 2026](https://arxiv.org/abs/2610.09934)).
- In GigaSpeech 3, predicted dialect labels raised macro-average WER from 23.62 to 25.51. This was seen only in a search summary ([GigaSpeech 3](https://arxiv.org/pdf/2611.02476)).
- Gnani's self-reported Hinglish telephony numbers put a language-ID cascade behind a unified model at switch points: 29.3% versus 21.4% switch-point error. Gnani's own figure and table disagree, so treat this loosely ([Gnani](https://gnani.ai/resources/research/code-switching-at-8khz)).
- Basque–Spanish systems that skip segmentation entirely reached 2.67% WER on parliament speech ([HiTZ-Aholab](https://www.isca-archive.org/iberspeech_2024/herranz24_iberspeech.html)).

Parakh already runs every recogniser on the whole segment. That is right, and per-segment language ID should not be added.

**Fusion pays only with independent witnesses.** The same shared tasks show what makes fusion pay. Itgan's mixed-dialect gain came from adding a "decorrelated system-combination member". RECOVER's English entity corrector reached **E-WER 7.44–7.96 from one hypothesis each of five vendors, against 9.76 from five temperature samples of one model** ([RECOVER](https://arxiv.org/html/2603.16411)).

Saaras v3 and v4 come from the same vendor. If Parakh lets a Saaras v3 hypothesis corroborate a Saaras v4 one, the two votes may really be one. A mishearing they share then becomes an "unprompted, corroborated" name and is written into memory. The fix:

- measure pairwise error overlap between the three recognisers on dev;
- require one Sarvam witness and one OpenAI witness before a name counts as corroborated.

The vendor ranking supports Saaras as the base text. On Voice of India's Hindi phone-call leaderboard, Saaras v3 scores **3.69 OI-WER against 6.94 for GPT Transcribe**. Amazon Transcribe is fifth at 4.69, which makes it a possible third vendor inside the AWS account Parakh already has ([Voice of India](https://voiceofindia.ai/stt)).

**What happens when an LLM writes transcript text.** Intron Health's medical studies show the result:

- LLM correction helped weaker recognisers: Azure on Nigerian speech went from 0.274 to 0.239 WER.
- It **made the strongest recogniser worse: Gemini went from 0.102 to 0.129**.
- It degraded output consistently when a model corrected its own transcript.
- It inserted extra medication terms and deleted body-measurement values ([Intron, arXiv 2501.15310](https://arxiv.org/html/2501.15310v1)).

The only peer-reviewed Hindi study found the same pattern: GPT-4o-mini zero-shot correction took IndicConformer from 18.02 to 25.14 WER ([Kumar et al., EACL 2026](https://aclanthology.org/2026.eacl-short.45.pdf)). Japanese multi-pass work agrees. Fusing several systems cut CER from 12.91 to 7.07, while single-system LLM correction was harmful on low-error audio ([Ko et al.](https://arxiv.org/html/2408.16180v2)).

Parakh's LLM only proposes candidates and pronunciations and never writes transcript text, which is the configuration this evidence allows. Two corollaries follow:

- **Numbers.** Number spans that both vendors agree on should be frozen. Number normalisation should run once, deterministically, on the stitched call rather than on each 24-second segment, so an amount split across a pause is not mangled.
- **Headline metric.** Intron's clinical-accent study found that recognisers with low general WER still made many entity errors ([Afonja et al.](https://arxiv.org/abs/2406.12387)). Names, not WER, should be the headline.

**Code-switching specifics.** Errors concentrate in the embedded-language words and at switch points. ServiceNow found that errors "concentrate on the English portions" of bilingual speech, and that Whisper translates into English when no language is set ([ServiceNow](https://huggingface.co/blog/ServiceNow-AI/code-switching)). Several audio LMs tested on Yoruba–English translated, padded their output or leaked their prompt ([arXiv 2609.11786](https://arxiv.org/abs/2609.11786)). gpt-transcribe belongs to the same family, so:

- pass `languages` explicitly on every call;
- down-weight an output whose script mix diverges sharply from Saaras's, as a likely translation;
- check hinted outputs for prompt leakage.

Aggregate metrics hide these failures. In KIT's PIER study, fine-tuning improved Spanish–English WER from 29.43 to 27.94, while the error on English words **rose from 36.41 to 50.78** ([PIER](https://arxiv.org/html/2501.09512v2)).

Prompts help when they are short and fixed, and fail when they are long or change per utterance. On Hinglish lectures, a one-line description cut error by a further 9.73%, while per-utterance language-pattern prompts "mostly fail" ([CLEAR](https://aclanthology.org/2025.icnlsp-1.33.pdf)). Prompting Whisper with another system's first-pass words cut Arabic WER by 22% relative with no training ([Talafha et al.](https://arxiv.org/html/2511.18774)). That is a cheap dev-set experiment for the hinted pass, not a change to make before the freeze.

**A closed vocabulary is Parakh's moat.** The biggest measured gain in any minority-language system came from restricting vocabulary to the domain. Bangor University's Welsh voice assistant scored **4.18% WER with a domain template-and-slot language model, against 18.06%** for a stronger general model ([Jones 2022](https://aclanthology.org/2022.cltw-1.8.pdf)). RECOVER's gain fell from 28.2% to 8.1% relative as list coverage fell from 100% to 25% ([RECOVER](https://arxiv.org/html/2603.16411)).

A trader's own contacts and suppliers are exactly that closed list. That is why Parakh's personal context matters more than any decoding trick. It is also why the discovery step, which raises coverage, earns its place, provided its names stay unverified candidates. Bangor's Welsh sentence-collection word list deliberately kept the English brand and company names people actually say. Microsoft Teams draws on meeting invitees ([Teams](https://techcommunity.microsoft.com/t5/microsoft-teams-blog/live-transcription-with-speaker-attribution-now-available-in/ba-p/2228817)). In the same spirit, discovery should add the commodity, unit and payment-app words traders use.

## Parakh's evidence is honest but too small for its sharpest claim

**What the current numbers support.** The FLEURS lead over raw Saaras v4 (+9.3 points, CI +4.8 to +14.5) is solid. The lead over gpt-transcribe with keywords (+5.7, CI +0.7 to +11.7) is not yet. Treat each name mention as a paired right/wrong outcome and use an exact McNemar test at 80% power. With **100 mentions it detects only gains of 8–13 points, and with 200 mentions 4–8.5 points**. A 5-point gain needs **about 155 to 470 mentions**, depending on how often the two systems disagree. These figures were computed with Connor's formula ([SAS PROC POWER](https://support.sas.com/documentation/cdl/en/statug/66103/HTML/default/statug_power_details55.htm); [worked example](https://cttir.github.io/tutorials/tutorials/sample-size/power-mcnemar.html)). At 140 mentions, a confidence interval that brushes zero is exactly what a real 5-point gain would look like.

The other results need careful framing:

- **The tie with Saaras v4 given each utterance's own names (95.7%)** is a strength if framed honestly. Given a 100-name list, Parakh matched a recogniser that was handed the answer key.
- **The trade-call result (14 of 14)** was tuned on those same calls, so it is dev evidence only.
- **The IndicContextEval result is the most under-sold.** Names tied with Saaras v4, but keyword-biased gpt-transcribe wrote **16 list terms that were never spoken, against Parakh's 1**. AssemblyAI warns that keyterm "hit rate always improves, so it hides regressions" ([AssemblyAI](https://www.assemblyai.com/blog/when-keyterm-prompting-backfires)). No vendor publishes a false-insertion rate for Indian speech.

**Use the literature's metric names.** Each of these quantities has a standard name, and using it makes the claim easy to read.

- **Entity metrics should lead.** KeyASRBench found keyword error rates of 13.61–33.81% where the overall error was 5.31–12.91%, **two to three times higher** ([KeyASRBench](https://arxiv.org/abs/2611.10852)).
- **"Names right"** is PIER, with names as the points of interest.
- **Collateral damage** is U-WER, the error on words outside the bias list, the standard companion to biased-word error ([arXiv 2104.02194](https://arxiv.org/pdf/2104.02194)).
- **"Names written but not said"** is a false-alarm rate in the keyword-search sense. NIST combines misses and false alarms into ATWV, with an explicit cost weight β on false alarms ([NIST OpenSAT20](https://www.nist.gov/system/files/documents/2020/04/15/2020_OpenSAT20_Eval_Plan_V1.5.pdf)).
- **Abstentions are a separate outcome.** Flagged names must be reported on their own, not counted as right or wrong. Dialogue-systems work found false acceptances cost more than false rejections ([Skantze 2007](https://preview.aclanthology.org/fix_video/2007.sigdial-1.35.pdf)).
- **An LLM judge should not be the primary metric.** The only Hindi-validated rubric, LASER, gives no penalty for proper-noun and number variants, by design ([LASER](https://arxiv.org/html/2510.07437v1)).

**Normalise Devanagari safely.** Whisper's `BasicTextNormalizer` replaces every Unicode mark with a space, so "मेरा नाम राहुल है" becomes "म र न म र ह ल ह" ([Whisper basic.py](https://raw.githubusercontent.com/openai/whisper/main/whisper/normalizers/basic.py)). It **cut reported Hindi WER on FLEURS by 21.9 points**, and the same normaliser was adopted by MMS, Seamless and Hugging Face evaluations ([Manohar & Pillai](https://arxiv.org/html/2409.02449v4)). Parakh's 5.2% versus 6.0% WER is meaningful only if no such normaliser touched it.

A defensible Devanagari scorer:

- applies Unicode NFC;
- decomposes the nukta letters that NFC leaves composed;
- removes zero-width joiners;
- maps Devanagari digits to ASCII;
- strips only punctuation and symbols, never vowel signs or other marks;
- reports a strict variant and a lenient one that also folds nukta, chandrabindu and homorganic nasals.

indic-nlp-library's normaliser does not apply NFC itself, so add it ([indic_normalize.py](https://raw.githubusercontent.com/anoopkunchukuttan/indic_nlp_library/master/indicnlp/normalize/indic_normalize.py)).

Converting both sides to one script for a script-tolerant WER is standard practice. SN-WER found that the choice of transliterator changed scores by **under 0.002**, with token collisions **under 0.1%** ([SN-WER](https://aclanthology.org/2026.mellm-1.24.pdf)). Plain WER overstated system gaps about threefold on Arabic–English speech ([Perle](https://arxiv.org/abs/2605.19069)).

**Test data and statistics.** FLEURS is read speech; the product is phone calls.

- **Telephony slice.** An IISc-affiliated study found GSM coding consistently degrades Hindi WER, while narrowband and wideband audio stay close to 16 kHz quality. Neural restoration such as VoiceFixer and AudioSR **made WER worse** ([Factors affecting Indic ASR](https://arxiv.org/pdf/2606.09335)). An 8 kHz μ-law copy of every test clip, made with ffmpeg, is therefore a cheap and honest telephony slice.
- **Monsoon hi-IN.** This set (CC-BY-4.0) has 753 spontaneous clips recorded on phones. Its accepted-spelling lattice already includes names and numbers, so it gives a third-party check that nothing regressed. Its authors show why slicing matters: two systems tied on the leaderboard differed "almost fourfold" in regional sensitivity ([Monsoon](https://huggingface.co/datasets/VoiceArena/MonsoonASR-Open-ASR-leaderboard-hi-IN); [HF blog](https://raw.githubusercontent.com/huggingface/blog/main/open-asr-leaderboard-global-south.md)).
- **IndicContextEval.** It has 3,110 Hindi utterances, and its adversarial wrong-domain entity lists stress-test false insertions ([IndicContextEval](https://huggingface.co/datasets/ai4bharat/IndicContextEval)).
- **Bootstrap unit.** Mentions in one utterance or call share a speaker, so the bootstrap should resample utterances or speakers, not mentions ([Bisani & Ney](https://www-i6.informatik.rwth-aachen.de/~bisani/bootlog.html); [block bootstrap](https://ar5iv.arxiv.org/html/1912.09508)).

## Production stacks learn only from confirmed corrections and mark uncertainty sparingly

**How production systems learn from users.** Systems that learn from users either keep implicit signals out of memory or put thresholds on them.

- **Dragon** updates a speaker profile only from its correction menu. It warns that "correcting" a word it actually got right makes recognition worse ([Dragon](https://nuance.com/products/help/dragon/dragon-for-mac/enx/Content/Correction/AboutCorrection.htm)).
- **Alexa's** self-learning rewrites won A/B tests by a ratio of 11.8 to 1 and cut defects by over 30% ([Amazon](https://ar5iv.arxiv.org/html/1911.02557)). A follow-up warned that models retrained on such feedback "can learn false equivalences" ([NAACL 2022](https://preview.aclanthology.org/fix_video/2022.naacl-industry.36.pdf)).
- **Gboard** keeps a newly discovered word only if roughly 45 users contribute it ([Gboard](https://arxiv.org/html/2404.11607v2)).
- **MINJA** injected false records into LLM-agent memory through ordinary queries alone, with 98.2% success ([MINJA](https://arxiv.org/abs/2503.03704)).

Parakh's "remember automatically once corroborated" is implicit learning without those guards. Two correlated recognisers can both mishear a name. The wrong name then enters memory, memory feeds the next call's candidates, and the error compounds silently. The fix is a two-tier memory:

- Corroborated names become **candidates**: they can be retrieved and offered as alternatives.
- **Verified** names need either a user's tap or cross-vendor corroboration in at least two separate calls.
- No transcript text and no LLM output can ever promote a name.

Bias lists should stay short. AssemblyAI advises starting with no keyterms and adding terms only after misses ([AssemblyAI keyterms](https://www.assemblyai.com/docs/universal-streaming/keyterms-prompting)). Amazon warns against storing personal data in vendor-side vocabularies ([Amazon Transcribe](https://docs.aws.amazon.com/transcribe/latest/dg/custom-vocabulary.html)).

**Showing uncertainty.** The APIs Parakh uses expose almost no word-level confidence. gpt-live-transcribe returns none. Saaras returns only a language probability. Token logprobs exist only on the deprecated gpt-4o transcription models ([OpenAI reference](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create); [Sarvam Saaras](https://docs.sarvam.ai/api/getting-started/models/saaras.md)). Agreement between vendors is therefore the confidence signal, and Parakh already computes it.

HCI research has settled how to show it. Across nine commercial ASR services, word confidences detected errors with an F1 of only 0.33–0.55. In a 36-person study:

- highlighting about 4% of words was rated more useful than highlighting 13–21% (4.1 versus 3.3);
- highlighted errors had **2.64 times the odds of being fixed**;
- even so, 16 participants preferred no highlighting at all ([CHI EA '25](https://arxiv.org/html/2503.15124v1)).

Apple's dictation uses the same sparing pattern: a blue underline and tap-for-alternatives ([Apple](https://support.apple.com/en-asia/guide/iphone/dictate-text-iph2c0651d2/14.0)). For Parakh that means three tiers:

- names that the vendors agreed on, or that are verified, carry no mark;
- names resolved by cross-examination get a quiet "did you mean" chip;
- disputed person names appear as an explicit question with alternatives.

Each tap is both a correction and the only route into verified memory.

**Correction loops and progressive display.** European minority-language services built exactly this correction loop. Bangor's Welsh transcriber gives each speech segment its own playback, a text box and a commit button. It deletes content after 30 days and reuses corrections only if the user opts in ([Jones 2022](https://aclanthology.org/2022.cltw-1.8.pdf)). Ireland's Fotheidil feeds human corrections back into training ([Fotheidil](https://arxiv.org/html/2501.00509v1)).

Streaming systems add a contract for how text appears and is later improved:

- Google's two-pass recogniser rescored its final output for a 17–22% relative WER cut, adding under 200 ms of finalisation latency ([Sainath et al.](https://arxiv.org/abs/1908.10992)).
- Azure replaces only the final result with a refined second pass ([Azure](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-recognize-speech)).
- AssemblyAI tells clients to replace rendered text rather than append to it ([AssemblyAI turn detection](https://www.assemblyai.com/docs/universal-streaming/turn-detection)).

Parakh can borrow this contract without real-time streaming. Show each segment's Saaras v4 text as soon as it arrives, replace it by segment ID when verification finishes, and run the 10–35-second discovery step without blocking the page.

## A thin async service in Mumbai covers production plumbing and India's privacy rules

**Vendor limits shape the service.** Sarvam's REST endpoint accepts at most 30 seconds of audio per request, at **60 requests a minute on pay-as-you-go**. It documents no Retry-After header and asks clients to retry a 503 like a 429. A 402 means credits are exhausted and must not be retried ([Sarvam FAQ](https://docs.sarvam.ai/api/speech-to-text/faq); [Sarvam rate limits](https://docs.sarvam.ai/api/getting-started/ratelimits)). gpt-transcribe starts at 5,000 requests a minute ([OpenAI](https://developers.openai.com/api/docs/models/gpt-transcribe)), so Sarvam is the binding constraint. A three-minute call cut into eight segments and sent to two Saaras models is 16 requests. That is about four calls a minute per account at pay-as-you-go limits.

Running several recognisers plus cross-examination cannot fit inside one HTTP request, so the transcription vendors' own pattern fits: submit, get a 202 with a job ID, wait for a notification or poll, then fetch the result. AssemblyAI's webhooks carry only an ID and a status, must be acknowledged within 10 seconds, and are not retried on 4xx errors ([AssemblyAI webhooks](https://www.assemblyai.com/docs/deployment/webhooks)). The Idempotency-Key header, which makes it safe to resubmit a job, is still an IETF draft ([IETF](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)).

**AWS.** App Runner closed to new customers on 30 April 2026, and AWS now points to ECS Express Mode instead. One API call with a container image and two IAM roles provisions a Fargate service with an HTTPS load balancer and autoscaling, in 3–5 minutes, at no extra charge ([AWS](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)). Lambda is cheaper, but it caps synchronous payloads at 6 MB and asynchronous ones at 1 MB, and new accounts get reduced concurrency ([Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)). Either way, audio must arrive through S3 presigned uploads ([S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)).

Mumbai (ap-south-1) charges the same Fargate prices as Hyderabad, and unlike Hyderabad it lists Amazon Transcribe ([ECS ap-south-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ap-south-1/index.json); [Transcribe ap-south-1](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/transcribe/current/ap-south-1/index.json)). Whether Express Mode is available in ap-south-1 was not confirmed, so check that first.

**India's privacy law.** Most of the obligations under India's Digital Personal Data Protection (DPDP) Act **start on 13 May 2027**: notice, consent, security safeguards, breach notice, erasure and the cross-border rules. Until then, section 43A of the IT Act and the 2011 SPDI Rules apply ([Khaitan & Co](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)). Building to the final rules now is still right. They require:

- a standalone notice listing the data items, the purpose and a withdrawal link;
- a breach report to the Data Protection Board within 72 hours;
- one year of breach-detection logs.

They also carry penalties of up to ₹250 crore for weak safeguards ([PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)).

The legality of call recording itself is unsettled. In 2025 the Supreme Court held covertly recorded spousal calls admissible as evidence, while several High Courts treat recording without consent as a privacy violation ([LiveLaw](https://www.livelaw.in/top-stories/secretly-recorded-telephonic-conversation-of-spouse-admissible-in-matrimonial-cases-supreme-court-297390); [Bar & Bench](https://www.barandbench.com/news/chhattisgarh-high-court-recording-conversations-without-consent-right-to-privacy)). Consent from every party on the call, confirmed with each upload, is the defensible product position.

**Vendor and AWS settings close most of the remaining gap.**

- **OpenAI.** The `/v1/audio/transcriptions` endpoint keeps no abuse-monitoring logs and no application state. The chat and responses endpoints keep abuse logs for 30 days unless zero data retention is approved ([OpenAI](https://developers.openai.com/api/docs/guides/your-data)). India at-rest data residency is available for new API projects ([OpenAI](https://openai.com/index/introducing-data-residency-in-asia/)).
- **Sarvam.** Workspace data is kept **indefinitely until an Owner sets a retention period**; 0 days is available for model APIs ([Sarvam](https://docs.sarvam.ai/api/platform/data-retention)). These settings take minutes.
- **AWS cannot redact Hindi personal data for Parakh.** Comprehend's PII detection covers only English and Spanish, and Transcribe does not support redaction for hi-IN ([Comprehend](https://docs.aws.amazon.com/comprehend/latest/dg/supported-languages.html); [Transcribe](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)).
- **Presidio is the practical fallback.** It ships recognisers for Aadhaar (with checksum), PAN, GSTIN and other Indian identifiers, which work on digits and Latin text in any language ([Presidio](https://presidio.dataprivacystack.org/supported_entities/)).

## Conclusion

The cross-language evidence changes what Parakh should spend its remaining hours on. It does not need a new recogniser, a trained verifier or a cleverer LLM. Its hard part is already in place and matches what worked elsewhere, from SeACo's no-bias output to VISH's unbiased verification. What it has not yet adopted is the defensive engineering those systems built around the core:

- vetoes that cancel partial and collateral matches;
- a rule that two witnesses count as two only if they come from different vendors;
- a memory that cannot learn from its own output.

All three trade a little recall for precision. For names, where a wrong name in a call record costs more than a question, the evidence says that trade is right.

The claim to put in front of Equal is not mainly "more names right". It is closer to this: given a 100-name list, Parakh matches a recogniser that was handed the answer key, and it writes almost none of the unspoken names that keyword biasing writes. Nobody publishes that second number for Indian speech. It is also the cheapest to measure and the easiest to defend once the test set is big enough for the first. That sets the order of work: guardrails and a frozen test split before deployment. A deployed demo with unmeasured false insertions is a liability; a measured one is the product.

## (a) Ranked changes to Parakh

The rank combines how strong the evidence is, the value per hour, and whether later work depends on the change. Effort assumes the existing CLI pipeline is reused, not rewritten. Items 1–13 total about 12.75 hours and fit the window in (e). Items 14 and 15 are stretch goals. The build order in (e) groups items by dependency, so it does not follow the rank exactly.

| # | Change | Evidence | Expected effect | Effort (h) | Risk |
|---|---|---|---|---|---|
| 1 | **Freeze a test split and grow it to ≥300 name mentions before tuning anything.** Keep the 91 FLEURS and 109 IndicContextEval utterances as test. Add new held-out utterances and set aside a separate dev slice. Treat the three trade calls as dev only. | Minimum detectable gain at 80% power: 8–13 points at 100 mentions, 4–8.5 at 200. +5 points needs ~155–470 mentions ([SAS](https://support.sas.com/documentation/cdl/en/statug/66103/HTML/default/statug_power_details55.htm)). Current +5.7 has CI +0.7 to +11.7. | Every later threshold is tuned on dev only. The primary comparison can resolve gains of about 3–7 points. The gpt-transcribe lead is either confirmed or shown to be a tie. | 0.75 active; runs in background | Low. Sarvam's 60 requests/min makes runs slow, so start first. |
| 2 | **Upgrade the scorer to the literature's metrics.** Add: names right / wrong / flagged; Name-PIER; precision of committed names; false insertions per 100 words and per utterance; U-WER; strict and script-tolerant WER; CER; number accuracy; exact McNemar; a bootstrap that resamples utterances or speakers; and a printed minimum detectable effect. Use a Devanagari-safe normaliser. | [PIER](https://arxiv.org/html/2501.09512v2); [KeyASRBench](https://arxiv.org/abs/2611.10852); [B-WER/U-WER](https://arxiv.org/pdf/2104.02194); [Manohar & Pillai](https://arxiv.org/html/2409.02449v4); [SN-WER](https://aclanthology.org/2026.mellm-1.24.pdf) | Turns "16 vs 1" into a headline metric with a confidence interval, and makes the WER figures valid. | 1 | Low |
| 3 | **Require cross-vendor corroboration.** Measure pairwise error overlap of Saaras v3, Saaras v4 and gpt-transcribe on dev. An unprompted name counts as corroborated, and may be learned, only with one Sarvam and one OpenAI witness. | [Itgan](https://arxiv.org/abs/2610.09934) decorrelated member; [RECOVER](https://arxiv.org/html/2603.16411): five vendors 7.44–7.96 E-WER vs 9.76 from five samples of one model | Fewer wrong immediate accepts and fewer wrong memories. Some names that were accepted at once now go to cross-examination. | 0.5 | Low. A few more hinted calls. |
| 4 | **Add the production vetoes to the acceptance step.** Revert unless the complete name aligns to the disputed span. Reject hinted runs that changed words outside the span. One disputed span and at most 3 hints (rival spellings included) per call. Stricter evidence for 1–2-syllable names and names that are common words. Strip -ji/ne/ko/se/ka/ki/ke/wala and fold spacing. Normalise scores by name length. Reject proposals farther from the cross-vendor consensus than the base span. Sweep the threshold on dev. | [sherpa-onnx](https://k2-fsa.github.io/sherpa/onnx/hotwords/index.html); [WeNet](https://wenet-e2e.github.io/wenet/context.html); [CLOVA](https://api.ncloud-docs.com/docs/ai-application-service-clovaspeech-longsentence); [MERL](https://merl.com/publications/docs/TR2024-073.pdf); [H-PRM](https://arxiv.org/html/2508.18295v1); [DANCER](https://arxiv.org/abs/2403.17645); [Sudo](https://www.isca-archive.org/interspeech_2023/sudo23b_interspeech.pdf); [VISH](https://arxiv.org/abs/2610.27867) | Fewer false insertions and protected U-WER. Names right stays within about ±1–2 points. The flag rate rises slightly. | 1.75 | Medium. Gates that are too strict raise flags, so tune on dev only. |
| 5 | **Split memory into candidate and verified tiers.** Corroborated or discovered names are candidates: retrievable and offered as alternatives, but never accepted on memory alone and never sent as keyterms. Verified needs a user tap, or cross-vendor corroboration in ≥2 separate calls with no contradiction. Transcript text, LLM output and free edits never promote a name. Store provenance. Decay by uses × e^(−age/τ), with τ of 30–90 days. Add a delete endpoint. | [Dragon](https://nuance.com/products/help/dragon/dragon-for-mac/enx/Content/Correction/AboutCorrection.htm); [Alexa false equivalences](https://preview.aclanthology.org/fix_video/2022.naacl-industry.36.pdf); [Gboard](https://arxiv.org/html/2404.11607v2); [MINJA](https://arxiv.org/abs/2503.03704); [AssemblyAI](https://www.assemblyai.com/docs/universal-streaming/keyterms-prompting) | Stops a correlated mishearing from compounding across calls, and supplies the erasure story. | 0.75 | Low. Names are learned more slowly. |
| 6 | **Wrap the pipeline in an async job API.** FastAPI with: presigned upload; `POST /v1/jobs` with an Idempotency-Key, returning 202; a status route; a result route with evidence per edit; confirmations; DELETE. Add an in-process worker and an S3 cache keyed by audio hash and parameters. Add a request limiter per vendor, jittered retries on 429/5xx only (never 402), a circuit breaker per recogniser, and a `partial` job status. | [Sarvam limits](https://docs.sarvam.ai/api/getting-started/ratelimits); [AssemblyAI webhooks](https://www.assemblyai.com/docs/deployment/webhooks); [IETF Idempotency-Key](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/); [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html) | A production-grade interface. The demo can replay from cache if a vendor fails during judging. | 2.25 | Medium. New code written at night. |
| 7 | **Privacy and consent pack.** Sarvam retention set to 0 days. A dedicated OpenAI project. Discovery receives minimised text, with identifiers replaced by regex tokens, sent with `store=false`. A standalone notice plus confirmation that every party consented. Contact display names only. Audio deleted after 24 h. Logs with no transcript content. | [Sarvam retention](https://docs.sarvam.ai/api/platform/data-retention); [OpenAI data](https://developers.openai.com/api/docs/guides/your-data); [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf); [Presidio](https://presidio.dataprivacystack.org/supported_entities/); [Comprehend](https://docs.aws.amazon.com/comprehend/latest/dg/supported-languages.html) | Answers the judges' first privacy questions. Matches the shape of DPDP Rule 3 well before 2027. | 1 | Low |
| 8 | **Deploy on ECS Express Mode in ap-south-1.** Build an arm64 image, push it to ECR, and make one `create-express-gateway-service` call. Add Secrets Manager, an S3 lifecycle rule and CORS, and 1-year log retention. | [AWS App Runner notice](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html); [ECS ap-south-1 prices](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ap-south-1/index.json) | A deployed link at about $1.5 a day. | 1.5 | Medium. Availability in ap-south-1 is unverified; fall back to a recorded demo. |
| 9 | **Demo UI with sparse, tiered marking.** Names the vendors agreed on, or verified names, are unmarked. Cross-examined names get a chip. Disputed names appear as a question with alternatives. Aim for 3–5% of words marked. Add an evidence drawer per edit and one-tap confirm. Show each segment's Saaras v4 text first and replace it by segment ID when verification finishes. Show the cost per call. | [CHI EA '25](https://arxiv.org/html/2503.15124v1); [Apple](https://support.apple.com/en-asia/guide/iphone/dictate-text-iph2c0651d2/14.0); [Jones 2022](https://aclanthology.org/2022.cltw-1.8.pdf); [AssemblyAI](https://www.assemblyai.com/docs/universal-streaming/turn-detection) | Users see why each name was written. Each tap feeds verified memory. | 1.75 | Medium. UI work expands; drop progressive display first. |
| 10 | **Cost and latency observability.** One JSON log line per vendor call and per job (vendor, model, audio seconds, latency, status, retries, cost). p50/p95 latency via CloudWatch Logs Insights. An AWS Budgets alarm. A daily audio-minutes cap per user. | [CloudWatch prices](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/ap-south-1/index.json); [Sarvam SLOs](https://docs.sarvam.ai/api/integration/livekit-production-best-practices) | Cost per call and p95 latency on a slide, plus a budget guard. | 0.5 (inside #6) | Low |
| 11 | **Number and script hygiene.** Run number normalisation once, on the stitched call. Freeze numbers that both vendors agree on, and flag the ones they disagree on. Always pass `languages`. Down-weight a recogniser whose script mix suggests it translated. Strip `<`, `>` and line breaks from hints, because OpenAI rejects the whole request otherwise. | [Intron](https://arxiv.org/html/2501.15310v1); [Kumar et al.](https://aclanthology.org/2026.eacl-short.45.pdf); [ServiceNow](https://huggingface.co/blog/ServiceNow-AI/code-switching); [OpenAI STT guide](https://developers.openai.com/api/docs/guides/speech-to-text) | Fewer amounts broken at segment cuts, no silently translated recogniser, no rejected requests. | 0.25 | Low |
| 12 | **Telephony A/B.** Send native 8 kHz and classically resampled 16 kHz audio to each API on dev, and record the rate sent. Add a μ-law test slice. | [Factors](https://arxiv.org/pdf/2606.09335); [Saaras v4 8 kHz](https://docs.sarvam.ai/api/getting-started/models/saaras.md); [Sarvam FAQ](https://docs.sarvam.ai/api/speech-to-text/faq) | Picks the better input format per vendor and shows robustness on the phone channel. | 0.25 active | Low |
| 13 | **Run Saaras v3 only on disagreement**, if the ablation shows it adds little. Keep it as the Equal baseline in the evaluation. | v3 is "legacy" ([Sarvam API](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe)); Equal runs v3 in translit mode ([Sarvam: Equal](https://www.sarvam.ai/stories/equal)) | Vendor ASR cost falls from ~₹1.5 to ~₹1.1–1.2 per minute. | 0.5 | Medium. A useful vote may be lost. |
| 14 | *Stretch:* choose each name's hint script (Devanagari, Latin, or both) on dev. | [MERL](https://merl.com/publications/docs/TR2024-073.pdf); [IndicContextEval](https://arxiv.org/html/2606.19157v2) | Possibly a few points on cross-examined names. | 1 | The dev result may be too noisy to read. |
| 15 | *After the freeze:* add Amazon Transcribe hi-IN as a third vendor, with a custom vocabulary of verified names. | [Voice of India](https://voiceofindia.ai/stt) 4.69 OI-WER; [Transcribe hi-IN](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html); [Transcribe price](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/transcribe/current/ap-south-1/index.json) | Three truly independent recognisers. | 3 | On code-switched audio, language ID can drop the vocabulary unless hi-IN is fixed. |

## (b) What to deliberately not do

| Don't | Why | Instead |
|---|---|---|
| Split calls by language or dialect and route pieces to specialist recognisers | A learned router recovered 44% of the perfect-routing gain ([Itgan](https://arxiv.org/abs/2610.09934)). Predicted language labels raised WER from 23.62 to 25.51 ([GigaSpeech 3](https://arxiv.org/pdf/2611.02476)). Language-ID errors "cannot be recovered" ([survey](https://arxiv.org/pdf/1904.00784)). | Run every recogniser on every segment and fuse. |
| Let any LLM write transcript text or digits, or correct its own output | Correction hurt the strongest recogniser and deleted measurement values ([Intron](https://arxiv.org/html/2501.15310v1)). Hindi WER went from 18.02 to 25.14 ([Kumar et al.](https://aclanthology.org/2026.eacl-short.45.pdf)). | The LLM proposes candidates and pronunciations only; numbers are normalised by rules. |
| Send the whole contact book or memory as keywords or keyterms | Error rose from 3.24 to 29.42 at 50 hints ([H-PRM](https://arxiv.org/html/2508.18295v1)). Biased-word error got 39–570% worse with 250 distractors ([Huber & Waibel](https://arxiv.org/html/2608.05759)). Parakh's own data: 16 false insertions vs 1. | At most 3 hints per disputed span. Up to 50 verified names in keyterms, only if dev shows it helps. |
| Count Saaras v3 agreeing with v4 as independent corroboration | Fusion gains come from independent members ([Itgan](https://arxiv.org/abs/2610.09934); [RECOVER](https://arxiv.org/html/2603.16411)). | Require one Sarvam and one OpenAI witness. |
| Promote names to memory from transcripts, discovery or free edits | Dragon, Alexa's false equivalences, MINJA's 98.2% injection success ([MINJA](https://arxiv.org/abs/2503.03704)). | Candidate and verified tiers; only user action or repeated cross-vendor agreement promotes. |
| Score Devanagari with Whisper's or Hugging Face's normaliser | It turns vowel signs into spaces, creating 21.9 points of illusory WER gain ([Manohar & Pillai](https://arxiv.org/html/2409.02449v4)). | An NFC-based Devanagari normaliser, with strict and lenient variants. |
| Tune on the test split, present the trade calls as held-out, or compare against leaderboard ranks | Voice of India runs models on default settings with no biasing lists ([VoI methodology](https://voiceofindia.ai/methodology)). | A frozen split scored once; trade calls labelled as dev. |
| Make an LLM judge the primary metric | LASER gives no penalty for proper-noun and number variants ([LASER](https://arxiv.org/html/2510.07437v1)). | Rule-based name and number metrics as primary. |
| Highlight every uncertain word | Confidence F1 is only 0.33–0.55, and heavy highlighting was rated less useful ([CHI EA '25](https://arxiv.org/html/2503.15124v1)). | Mark about 3–5% of words, by tier. |
| Neurally upsample 8 kHz audio | VoiceFixer and AudioSR made WER worse ([Factors](https://arxiv.org/pdf/2606.09335)). | Native 8 kHz or classical resampling, chosen by A/B test. |
| Build live streaming or full duplex before the async path is solid | This is a post-call product, and refining one segment at a time already gives the two-pass experience ([Azure](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-recognize-speech)). | Progressive segment refinement in the UI. |
| Train or fine-tune anything, or add a local CTC verifier or learned retriever | List-size failures appear at thousands of entries ([SeACo](https://arxiv.org/html/2308.03266v4); [H-PRM](https://arxiv.org/html/2508.18295v1)); Parakh's lists hold about 100. | Keep the phonetic key and tune thresholds on dev. |
| Use App Runner, or carry audio through Lambda's synchronous payload or long load-balancer requests | App Runner is closed to new customers ([AWS](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html)); Lambda caps synchronous payloads at 6 MB ([Lambda](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)). | ECS Express, presigned S3 uploads, and 202-then-poll. |
| Retry Sarvam 402s or any 4xx error, or retry without jitter | A 402 means credits are exhausted ([Sarvam](https://docs.sarvam.ai/api/getting-started/ratelimits)). | Jittered exponential backoff on 429 and 5xx only. |
| Send phone numbers, whole address books or raw identifiers to the LLM, or log transcripts | Contacts are other people's personal data, and chat endpoints keep 30-day abuse logs ([OpenAI](https://developers.openai.com/api/docs/guides/your-data)). | Display names only, minimised tokenised text, logs without content. |
| Install NeMo/pynini on the Mac under time pressure | pip installation is unsupported on macOS ([NeMo](https://github.com/NVIDIA/NeMo-text-processing)). | Keep the rule-based number normaliser. |

## (c) Architecture of the production-ready version

### Request flow and pipeline

```
Browser/demo ──POST /v1/uploads──► API (FastAPI, Fargate arm64, ap-south-1)
     │  PUT audio via presigned URL (SHA-256 checksum)
     ▼
 S3 audio/ (deleted after 24 h) ◄── POST /v1/jobs (Idempotency-Key) → 202 {job_id}
                                      │ in-process worker (asyncio; one task)
  segment at pauses (≤24 s) → recognisers in parallel:
      Saaras v4 (base text) · gpt-transcribe (languages=[hi,en]) · Saaras v3 (on disagreement)
  → matching key (Devanagari-safe, romanised) → align, flag disputed spans
  → retrieve candidates: verified ▸ candidate ▸ call's contacts ▸ discovery (async)
  → corroborate (needs one Sarvam + one OpenAI witness)
  → cross-examine (≤3 hints, one span per call, 3 hint orders, abstain)
  → vetoes (complete name, no collateral shift, short/common-word gate, consensus distance)
  → write into Saaras v4 base → stitch segments → rule-based number normalisation once
  → result + evidence per edit + flags
 S3 cache/ (audio hash + params) · DynamoDB jobs / idempotency / memory · CloudWatch JSON logs
```

Each segment's Saaras v4 text is available as soon as it returns and is replaced by segment ID once verification finishes. Discovery runs in parallel and can only add candidates; it never blocks a segment. If a recogniser's circuit breaker is open, the job degrades:

- with all three recognisers, the full rules apply;
- with only the cross-vendor pair, the full rules minus the v3 vote apply;
- with a single recogniser, no name is auto-accepted, every disputed name is flagged, and the job is marked `partial` with the missing recognisers listed.

### API surface

| Route | Purpose | Notes |
|---|---|---|
| `POST /v1/uploads` | Returns `{audio_id, upload_url, expires_at, required_headers}` | Presigned S3 PUT with a SHA-256 checksum header. Role credentials expire with the session. |
| `POST /v1/jobs` | `{audio_id, user_id, context:{names[]}, retention}` → `202 {job_id}` | Idempotency-Key. Same key and body returns the original job; a different body returns 422; a job still in flight returns the existing job. |
| `GET /v1/jobs/{id}` | Status: queued, transcribing, verifying, completed, partial or failed | Per-recogniser status and latency, cost so far. |
| `GET /v1/jobs/{id}/result` | Transcript, edits with evidence, flags | Includes `pipeline_version` and vendor model IDs. |
| `POST /v1/jobs/{id}/confirmations` | User resolves a chip or flag | The only route that promotes a name to verified. |
| `DELETE /v1/jobs/{id}`; `GET/DELETE /v1/users/{id}/memory` | Erasure | Deletes audio, transcript, cache entries and token vault; or the user's memory. |
| Webhook (designed for, not built) | `{job_id, status, event_id}`, HMAC-SHA256 signature | Success = 2xx within 10 s. No retry on 4xx; otherwise up to 10 retries with backoff, mirroring [AssemblyAI](https://www.assemblyai.com/docs/deployment/webhooks). |

Each edit carries its own evidence, which is the differentiator to show judges:

```json
{"edit_id":"e3","segment":7,"before":"मोहन","after":"Rohan","type":"person_name","tier":"chip",
 "evidence":[{"source":"saaras:v4","text":"मोहन","hinted":false},
             {"source":"gpt-transcribe","text":"Rohan","hinted":false},
             {"source":"gpt-transcribe","hints":["Rohan","Mohan"],"orders":3,"votes":{"Rohan":3}},
             {"source":"memory","name_id":"n_19","tier":"candidate"}],
 "rule":"cross_vendor_unprompted+cross_exam_3of3","vetoes_passed":["complete_name","no_collateral","length"],
 "pipeline_version":"parakh-1.0.0"}
```

### Storage and memory tiers

| Store | Contents | Retention |
|---|---|---|
| S3 `audio/` (private, SSE) | Uploaded call audio | Lifecycle rule deletes after 24 h |
| S3 `cache/` | Raw recogniser outputs, keyed by `sha256(pcm) + vendor + model + mode + language + sorted(hints) + prompt hash` | Same as transcripts (30 days); replaces the on-disk cache |
| S3 `results/` | Transcript, edits, evidence | 30 days, or until DELETE |
| DynamoDB `jobs`, `idempotency` | State, cost, per-recogniser status; idempotency records | Jobs 30 days; idempotency 24 h TTL |
| DynamoDB `memory` | Per user: canonical name, spellings, simple romanised pronunciation, tier, provenance, uses, last confirmed, contradictions | Until the user deletes; decays out of the bias list |
| Secrets Manager | Sarvam and OpenAI keys | $0.40 per secret per month ([price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSSecretsManager/current/ap-south-1/index.json)) |

| Memory tier | How a name gets there | What it may do |
|---|---|---|
| Call context (temporary) | The contacts relevant to this call, and discovery output | Retrieval candidates only; deleted with the job |
| Candidate | Corroborated once across vendors, or discovered and then corroborated | Retrieval and alternatives in chips. Never accepted on memory alone, never a keyterm. |
| Verified | User tap, or cross-vendor corroboration in ≥2 separate calls with no contradiction | May be a keyterm (20–50 at most), may display unmarked, may break ties in chip order. Needs re-confirmation after two contradictions. |
| Never promotes | Transcript text, LLM output, free-text edits | Nothing (Dragon, Alexa and MINJA lessons) |

Memory is isolated per user. It is never pooled across users; if it ever is, a Gboard-style threshold of many independent users is needed ([Gboard](https://arxiv.org/html/2404.11607v2)).

### Privacy and consent

| Data item | Where it goes | Control |
|---|---|---|
| Call audio | S3 Mumbai; Sarvam, with workspace retention set to 0 days; OpenAI `/v1/audio/transcriptions`, which keeps no logs | Per-upload confirmation that all parties consented; deleted after 24 h; DELETE |
| Discovery input | Minimised transcript snippets with Aadhaar, PAN, phone, UPI and account numbers replaced by tokens (regex, or Presidio's Indian recognisers); `store=false` | Disclose OpenAI's 30-day abuse logs unless zero data retention is granted |
| Contacts | Display names only; only the shortlist for a call leaves the service | Per user; deletable |
| Logs | CloudWatch, kept 1 year for breach detection | No transcript text, names or numbers; token IDs and lengths only |

The consent screen is a standalone notice shaped like DPDP Rule 3. It lists the data items, the purpose ("correct names and numbers for you; no training, no ads"), the processors and their locations, the retention periods, a withdraw/delete link and a grievance contact, and it excludes under-18 users. The user ticks a box, and the timestamp and notice version are logged ([Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20Digital%20Personal%20%20Data%20Protection%20Rules%20-%2015%20November%202025.pdf)). A one-page breach runbook covers the 72-hour report to the Data Protection Board ([PIB](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)). Two options are worth mentioning on a slide without enabling them today: India-first routing, and an OpenAI project with India data residency ([OpenAI](https://openai.com/index/introducing-data-residency-in-asia/)).

### Deployment on AWS

Build one arm64 container and push it to ECR. Create one ECS Express service in ap-south-1: 0.5 vCPU, 1 GB, minimum and maximum one task. The single task keeps the in-process rate limiter valid; scaling out later needs SQS plus a limiter backed by DynamoDB. Express Mode expects a default VPC with public subnets ([ECS Express](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-getting-started.html)).

- The task role gets scoped S3 and Secrets Manager permissions only.
- The S3 bucket blocks public access, has lifecycle rules, and allows CORS from the demo origin.
- The fallback is a container-image Lambda triggered by S3 events, passing only the object key because of the 1 MB asynchronous payload cap.
- The last resort is the same container run locally plus a recorded demo, which the submission rules allow.

At scale, Sarvam's Batch API (files up to 2 h, 20 requests/min on pay-as-you-go) should do the unbiased first pass over whole calls, with REST reserved for hinted re-runs ([Sarvam FAQ](https://docs.sarvam.ai/api/speech-to-text/faq)). Sarvam's Growth tier raises REST limits to 4,000 requests a minute.

### Observability and resilience

**Logging.** Emit one structured line per vendor call: `{evt, job_id, vendor, model, audio_s, latency_ms, status, retries, cost_usd}`. Emit one per job with total cost, latency per stage, flag count and the share of segments that needed a hinted pass. The query `filter evt="vendor_call" | stats pct(latency_ms,50), pct(latency_ms,95) by vendor` gives percentile latency at CloudWatch's Mumbai prices ($0.67 per GB ingested) ([CloudWatch](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/ap-south-1/index.json)).

**Health page.** Show:

- p95 delay from segment end to verified text;
- flags per 100 words;
- chip acceptance, override and ignored rates (an ignored highlight is the warning sign from the CHI study);
- the share of segments that needed a hinted pass;
- the rate of degraded jobs;
- cost per audio minute;
- Sarvam 429 counts.

**Resilience.**

- A token bucket per vendor (Sarvam REST about 1 request/s, bursts of 5).
- Full-jitter exponential backoff, base 0.5 s, cap 8 s, at most 3 attempts, on 429, 5xx and timeouts only. Never retry 400, 401, 402 or 413.
- Timeouts per attempt: 25 s for Sarvam, 60 s for OpenAI.
- A circuit breaker per recogniser: it opens after 5 consecutive failures, and probes again after 30 s.

**Guards.** An AWS Budgets alert at $20. A daily audio-minutes cap per user that returns 429.

### Cost per audio minute

Assumes ₹88 per US dollar. Sarvam prices exclude GST ([Sarvam pricing](https://docs.sarvam.ai/api/getting-started/pricing); [OpenAI](https://developers.openai.com/api/docs/models/gpt-transcribe)).

| Line item | Unit price | Today | With Saaras v3 cascaded |
|---|---|---|---|
| Saaras v4 base | ₹0.49/min | ₹0.49 | ₹0.49 |
| Saaras v3 third witness | ₹0.49/min | ₹0.49 | ~₹0.10 (if it runs on ~20% of audio) |
| gpt-transcribe, unbiased | $0.0045/min | ₹0.40 | ₹0.40 |
| gpt-transcribe hinted re-runs | $0.0045 per segment-minute re-run | ₹0.08–0.24 (one segment in five, 1–3 runs) | ₹0.08–0.24 |
| LLM discovery | Per token | Not priced; log tokens and price from the chosen model's rate card | same |
| **Vendor speech recognition total** | | **≈₹1.46–1.62/min (~$0.017–0.018)** | **≈₹1.06–1.22/min (~$0.012–0.014)** |
| AWS fixed: Fargate arm64 0.5 vCPU/1 GB, load balancer, public IPv4 | ~$0.06/h | ~$1.5/day regardless of volume | same |

A three-minute trade call costs roughly ₹4.4–4.9 today. A single Saaras call would cost ₹1.47, so Parakh is about three times as expensive in exchange for verified names. Fargate is $0.02383 per vCPU-hour and $0.00261 per GB-hour; the load balancer is $0.0239 per hour plus usage; public IPv4 is $0.005 per hour per address ([ECS](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/ap-south-1/index.json); [ELB](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSELB/current/ap-south-1/index.json); [VPC](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonVPC/current/ap-south-1/index.json)).

## (d) Evaluation plan that makes the claim credible

### Datasets and splits

| Set | Role | Target size | Access | What it tests |
|---|---|---|---|---|
| FLEURS Hindi: the existing 91 utterances / 140 mentions | Test (frozen) | Keep as-is |, | Continuity with the reported numbers |
| FLEURS Hindi: new held-out utterances | Test | Together with the row above, ≥300 name mentions |, | Primary names claim against the 100-name list |
| FLEURS Hindi: separate slice | Dev | ~100 mentions |, | All tuning |
| IndicContextEval Hindi: the existing 109 plus new utterances | Test | ≥300 utterances, including native-script entity lists, adversarial wrong-domain lists, and ≥20% with no entity | CC BY 4.0 ([HF](https://huggingface.co/datasets/ai4bharat/IndicContextEval)) | Use of context, and false insertions under wrong context |
| "True name removed" lists | Stress test | For every test utterance: a list without the spoken name but with a sound-alike of it | Built from the existing lists | Echo rate and false replacement on Rohan/Mohan-type pairs |
| Monsoon hi-IN | External check that nothing regressed | 100–200 clips whose lattice has a name or digit slot | CC-BY-4.0 ([HF](https://huggingface.co/datasets/VoiceArena/MonsoonASR-Open-ASR-leaderboard-hi-IN)) | Spontaneous speech recorded on phones; OI-WER via `voi-oiwer` |
| 8 kHz μ-law copies of every test clip | Telephony slice | All | ffmpeg | Robustness to the phone channel ([Factors](https://arxiv.org/pdf/2606.09335)) |
| The three trade calls, plus any new consented calls | Dev and demo | 3 or more | Own recordings, with consent | In-domain behaviour; never quoted as held-out |

### Systems compared

| ID | Configuration | Question it answers |
|---|---|---|
| A | Saaras v3, translit mode, no biasing | Equal's documented production setup ([Sarvam: Equal](https://www.sarvam.ai/stories/equal)) |
| B | Saaras v4, no biasing | Parakh's base text |
| C | Saaras v4 + keyterms set to the 50 names Parakh's retrieval picks | Is Parakh just retrieval plus Sarvam's own biasing? |
| D | Saaras v4 + each utterance's own names | Upper bound for list biasing (the answer key) |
| E | gpt-transcribe, `languages=[hi,en]`, no keywords | OpenAI's unbiased baseline |
| F | gpt-transcribe + all 100 names as keywords | What a developer would naturally ship |
| G | Parakh, frozen | The claim |
| G− | Parakh without each of: cross-examination, order vote, discovery, memory, Saaras v3 | Which parts earn their cost |

### Metrics

| Metric | Definition | Why |
|---|---|---|
| Names right / wrong / flagged | Three-way outcome per reference mention, after mapping to the canonical spelling | Abstention honesty |
| Precision of committed names | right ÷ (right + wrong) | False acceptances cost more than flags |
| Name-PIER | Edit errors on name tokens ÷ name tokens ([PIER](https://arxiv.org/html/2501.09512v2)) | Literature anchor |
| Name false-insertion rate | List names written but not spoken, per 100 reference words and per utterance | The 16-vs-1 differentiator |
| ATWV-style cost | 1 − (miss rate + β·false-alarm rate), with β stated (for example, a wrong name counts 3× a missed one) ([NIST](https://www.nist.gov/system/files/documents/2020/04/15/2020_OpenSAT20_Eval_Plan_V1.5.pdf)) | One number for both errors |
| Echo rate of the hinted pass | Share of "true name removed" and no-name items where the hint appears in the output | A number no one has published |
| U-WER; strict WER; script-tolerant WER; CER | WER on words outside the name list; WER after the Devanagari-safe normaliser; WER after converting both sides to one script ([SN-WER](https://aclanthology.org/2026.mellm-1.24.pdf)); character error rate | Collateral damage and valid WER |
| Number accuracy | Exact match after rule-based normalisation of both sides to written form | Amounts and quantities |
| Operational | Flag rate, p95 latency, cost per minute, share of segments needing a hinted pass | Production readiness |

### Sample sizes and statistics

Declare one primary hypothesis in the README before running the test set. Parakh (G) beats the best non-oracle baseline (expected to be F) on names right, across the FLEURS and IndicContextEval test sets. Test it with an exact two-sided McNemar test on the per-mention discordant pairs, at α = 0.05. Report a 95% confidence interval from a 10,000-sample paired bootstrap that resamples utterances (speakers where known), never individual mentions.

The secondary tests are:

- the false-insertion rate of G versus F, by paired bootstrap or a sign test on per-utterance counts;
- U-WER non-inferiority against B, with the margin stated in advance (for example 0.5 points);
- the ablations, with Holm correction.

Compute the share of discordant mentions from the existing 140 FLEURS mentions, and choose the test size from this table (Connor's formula, 80% power, two-sided α = 0.05):

| Share of mentions where the systems disagree | Mentions needed to detect +5 points |
|---|---|
| 0.05 | ~155 |
| 0.07 | ~218 |
| 0.10 | ~312 |
| 0.15 | ~469 |

Print the minimum detectable effect next to every comparison, so that "no significant difference" reads as "underpowered" where it is. Clustering shrinks the effective sample by the design effect 1 + (m − 1)ρ. With three names per call and an intra-call correlation of 0.3, 150 mentions behave like about 94, which is why the bootstrap resamples calls. Report every table per slice as well as overall:

- clean versus μ-law;
- read versus extempore;
- name present versus absent;
- sound-alike in the list versus not.

The gate for future changes is a 30–60-clip golden set with hashed audio and references. A change fails if script-tolerant WER rises by more than the bootstrap half-width, or if any previously correct entity becomes a miss. For every run:

- pin vendor model IDs;
- record the sample rate sent to each API;
- use one normaliser for all systems.

As a rough estimate, 400 test utterances run through the Sarvam configurations come to under an hour of Sarvam time at 60 requests a minute, so the full test set fits in an overnight background job.

## (e) Hour-by-hour build order to the freeze

It is Saturday about 16:30 IST, and the freeze is Sunday 14:00: 21.5 hours, including about 5 hours of sleep.

| Window (IST) | Block | Exit criterion |
|---|---|---|
| Sat 16:30–17:15 | **Operations and split (items 1, 7).** Set Sarvam retention to 0 days; create a dedicated OpenAI project; set an AWS Budgets alert; confirm ECS Express exists in ap-south-1; create a private S3 bucket; tag the current CLI `v0`. Write the split manifest: existing test items, new held-out items, a separate dev slice, "true name removed" lists, μ-law copies. Start all baseline runs (A–F) in the background, cached and throttled to 60 requests/min. Start the Monsoon download. | Manifest hashed; baselines running |
| 17:15–18:15 | **Scorer (item 2).** Three-way outcome, Name-PIER, precision of committed names, false insertions, echo rate, U-WER, strict and script-tolerant WER, CER, number accuracy, McNemar, bootstrap, minimum detectable effect. | Reproduces the current numbers on old outputs |
| 18:15–19:00 | **Cross-vendor corroboration and hygiene (items 3, 11).** Measure overlap on dev; require cross-vendor corroboration; Devanagari-safe matching key; explicit `languages`; script-mix guard; hint sanitising; number normalisation on the stitched call. | Dev run shows the change in wrong auto-accepts |
| 19:00–20:45 | **Vetoes (item 4).** Unit tests on minimal pairs and the trade calls. | Dev false insertions down; names right within noise |
| 20:45–21:15 | Dinner |, |
| 21:15–22:15 | **Memory tiers (item 5); tokenised discovery input (item 7).** | Tests prove that transcript text and LLM output cannot promote a name |
| 22:15–01:00 | **Service (items 6, 10).** Routes, presigned upload, jobs with idempotency, worker, S3 cache, job state, rate limiters, retries, circuit breakers, `partial` status, evidence per edit, cost logs. | One trade call runs end to end through the local API and replays from cache |
| 01:00 | Start background runs: Parakh on dev, ablations (without v3, without the order vote, without cross-examination), and the 8 kHz versus 16 kHz A/B (item 12). |, |
| 01:00–06:00 | Sleep |, |
| 06:00–07:00 | **Tune on dev only.** Decide whether to cascade Saaras v3 (item 13). Freeze the configuration and tag `v1-frozen`. Start the frozen test runs on all test sets, clean and μ-law, in the background. | Configuration hash recorded before any test number is seen |
| 07:00–08:30 | **Deploy (item 8).** arm64 image to ECR, ECS Express, secrets, S3 lifecycle and CORS, log retention. | A public HTTPS URL processes a trade call |
| 08:30–10:30 | **UI (items 9, 7).** Consent screen and confirmation, upload, progressive segment display, three tiers, evidence drawer, one-tap confirm, delete buttons, cost per call. | The full demo flow works on the deployed URL |
| 10:30–11:15 | **Final numbers.** Tables per set and slice, McNemar, confidence intervals, minimum detectable effect, false insertions, echo rate, U-WER, cost per minute, p95 latency. | Results table frozen |
| 11:15–12:30 | **Slides, README and backup video.** Five slides: (1) the problem and Equal's v3 baseline; (2) how Parakh decides, shown through the evidence trail; (3) results: right/wrong/flagged with confidence intervals, false insertions, U-WER, telephony slice; (4) architecture, privacy and cost per minute; (5) limits (FLEURS is read speech, the trade calls are dev, the tie with answer-key biasing) and next steps (Amazon Transcribe as a third vendor, a consented real-call test set). | Slides and video exported |
| 12:30–13:30 | Buffer: bug fixes, scan the repo for secrets, check the bucket is private. |, |
| 13:30–14:00 | Code freeze: tag, push, submit. | Submitted |

If the schedule slips, cut in this order:

1. Progressive segment display (show only final text).
2. Monsoon.
3. The μ-law slice.
4. The Saaras v3 cascade (keep v3 always on).
5. AWS. If ECS Express is not serving by 08:30, run the container locally and submit the recorded demo instead of losing the morning to infrastructure.

Never cut these four:

- the frozen test split;
- the false-insertion metric;
- the retention and consent settings;
- the cross-vendor corroboration rule.

They are what make the claim checkable.
