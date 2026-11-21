# Parakh: context for anyone picking this up

Written Sat 21 Nov 2026, about 23:45 IST. Code freeze is Sun 22 Nov, 14:00 IST (Builders 2026,
Equal AI x OpenAI, Hyderabad; track "Build Challenging: Voice AI for India"). Solo build.
Judged on: a working end-to-end demo on fresh input, AI-native, presentation and craft.
Submission: code repository, deployed link or recording, 4-5 slides.

## What it is, in three sentences

Parakh (परख, the jeweller's test for gold) is a verification layer that sits after any speech
recogniser. It listens with three recognisers, finds the words they doubt, looks up which
names the user knows could sound like that, listens again with those as hints, and writes a
name only when the audio backs it; what it cannot settle it asks about, never guesses. Only
the user's confirmation moves a name into memory, so it learns names without learning
mistakes.

The pitch: it cuts a speech model's name errors by about 60% on all three models tested,
loses no name the model had right, needs no retraining, and is one changed URL to adopt.
It is NOT more accurate than the vendors' own keyword features when those are given the
right names (tie). It has nothing to add when no names are known.

## Layout

```
harness/
  parakh.py     the pipeline: listen -> doubt -> look up -> hear again -> decide (run(), Config)
  context.py    ContextIndex: names the user knows, phonetic keys, nearest(), build() asks for pronunciations
  phonetic.py   cross-script phonetic key (Devanagari <-> Roman), weighted edit distance, same_sound, similarity_at_least
  numbers.py    Indian spoken numbers -> digits by rule (lakh/crore/saadhe/dhai, Hindi 0-99), numbers_in(), to_digits()
  memory.py     per-user names in tiers: verified / candidates / rejected (data/memory/<user>.json); only a person promotes
  discover.py   gpt-5.5 reads all transcripts of a call, proposes topic + real-world names (used only if the audio backs them)
  pronounce.py  gpt-5.4-mini writes how a Roman-script name is said in Devanagari (data/pronunciations.json)
  dealsheet.py  gpt-5.5 fills a fixed form (what was agreed) from the checked transcript; en or hi
  render.py     word lists with marks (wrong / fix / num / unsure) and the evidence text per edit
  segment.py    split a call at pauses into <= 24 s segments (Sarvam REST takes < 30 s)
  service.py    FastAPI: the demo page's API, /speech-to-text, keys, saved calls, logs
  account.py    keys with a free allowance, per-request log, saved calls, running cost at list prices
  systems.py    recogniser adapters: Sarvam Saaras v3/v4 (REST, translit/transcribe), OpenAI gpt-transcribe, ElevenLabs, Deepgram; on-disk cache
  asr.py        OpenAI transcription with cache (.cache/asr)
  score.py      scorer: script-tolerant WER (jiwer), names right (span_hit), false insertions
  stats.py      paired bootstrap by clip, exact McNemar, minimum detectable effect
  fleurs.py     FLEURS Hindi benchmark runner (--set first|fresh, --bases, --phone, --alpha, --real, --stack, --jury, --vote, --no-context --discover)
  stress.py     sound-alike stress test: true names removed from the list, a sound-alike planted per name
  loop.py       learning-loop simulation: recordings played as one person's calls, names confirmed after each
  ice.py        IndicContextEval Hindi runner (ties; kept for honesty)
  call.py       CLI: process one whole call; compare.py/run_base.py/record.py/synth.py/data.py: early dev tools
scripts/
  build_scoreboard.py  collects runs/*.json into data/scoreboard.json, which the page reads
  prepare_fleurs.py / prepare_fleurs_fresh.py  tag names in the references (OpenAI), make 16-bit wavs, manifests
  measure_latency.py   times POST /speech-to-text on never-seen clips (adds silence so nothing is replayed)
  real_calls_table.py  scores the three private calls against data/real/truth.json
  build_samples.py     bundles the three calls into data/samples/
web/index.html          the demo page (single file). web/index-dark.html: an alternative theme, unlinked
deploy/aws.sh, setup.sh one t3.small in ap-south-1 with Caddy HTTPS; UNTESTED (user never ran aws configure)
tests/                  67 tests, no network: uv run pytest -q
data/                   context.json, pronunciations.json, scoreboard.json, samples/ (3 calls), memory/, calls/, keys.json, logs/
                        external/fleurs_hi (first set), external/fleurs_hi_fresh (test split), external/ice_hi; real/ (private calls)
runs/                   every measurement, .md table + .json per clip
.cache/                 every recogniser and LLM answer, keyed by audio bytes + parameters; reruns are free
```

Gitignored: .env, .cache/, data/external/, data/real/, data/samples/, data/uploads/, data/memory/,
data/calls/, data/keys.json, data/logs/. Keys live only in .env (OPENAI_API_KEY, SARVAM_API_KEY,
optional ELEVENLABS_API_KEY, DEEPGRAM_API_KEY). Nothing has been committed to git yet (user's
standing instruction: do not commit unless asked).

## Running it

```
uv sync && cp .env.example .env            # fill the two keys
uv run uvicorn harness.service:app --port 8000      # PARAKH_ACCESS_CODE=<code> gates new audio and key creation
open http://localhost:8000
uv run pytest -q
```
ffmpeg must be on the path. First request after start takes ~2 s (word lists load); then
the check itself is ~0.1 s per clip plus recogniser time.

Public demo right now: a cloudflared tunnel from the laptop (address changes on every restart;
new audio is gated by PARAKH_ACCESS_CODE, kept out of this file). `caffeinate -dims` keeps the
laptop awake. Demo path (calls 1-3 and their confirmations, en and hi) is fully cached.

## The pipeline, precisely (harness/parakh.py: run())

Config defaults: base "saaras-v4 translit"; witnesses saaras-v4, saaras-v3, gpt-transcribe (hi/en);
rivals=True; MAX_HINTS=8; FLOOR_SINGLE 0.80 / FLOOR_MULTI 0.70 / DISPUTED_DISCOUNT 0.12 /
FLOOR_BACKING 0.60 / FLOOR_ECHO 0.62. Benchmarks use base "saaras-v4" in transcribe mode
with a Devanagari script prompt for gpt-transcribe.

1. listen(): all witnesses in parallel, no hints; a failed one is dropped, not fatal.
2. disputed_positions(): per transcript, word positions others heard differently (alignment by phonetic key).
3. find_mentions(): runs of 1-4 words that sound like a known name (lower floor at disputed positions);
   everyday words (wordfreq top 5000 hi+en) are never treated as mishearings.
4. Shortlist = saved names + discovered names that >= 2 recognisers back. Corroborated = a recogniser
   wrote the name unprompted (same sound) AND another backs it (>= 0.60): accepted with no extra listen.
5. Others: one hinted gpt-transcribe pass with the shortlist + "rival" spellings (what two recognisers
   agreed on, offered in the transcript's own script) as keywords. A name is accepted if the hinted pass
   writes it. Sound-alike groups with no corroboration get two more passes with rotated hint order;
   accept only a clear winner (top >= 2 and >= 2x runner-up), else "unresolved" (asked).
6. Discovered-but-uncorroborated names are only suggestions. transplant() writes accepted names into
   the base transcript at the matching span; garbled repeats are rewritten only where no other
   recogniser backs the word.
7. unsure_spans(): name-like words no other recogniser backs -> questions (about 1% of words).
   number_doubts(): numbers compared by VALUE across recognisers; asked when nobody agrees with the base
   and someone heard a different number. A word that equals a confirmed name is never asked about.
8. Numbers -> digits by rule in render/to_digits. number_fixes(): a number the base alone got wrong is
   rewritten when both other recognisers agree on another value, or when the speakers' own multiplication
   ("chaalis into chaar", anywhere in the call) matches exactly one of the values heard; the same arithmetic
   drops a doubt when it backs the base (trace["number_checks"], shown on the number when clicked).
   Measured on 111 public numbers: fixed 0, broke 0 (there were no real base errors a recogniser had right).
   No LLM ever writes transcript text or digits.

Switched-off experiments kept in code (all measured, all worse or no better): consensus (majority on
name-like words: fixed nothing, WER up), accept_by_vote/own-lookup without context (+1.4 pts, p=0.5),
jury (three differently-ordered second listens), vote "2of3"/"openai+1" (vendor keyword passes as votes),
"stacked" (Parakh on Sarvam-with-retrieved-50: ties Sarvam's keyword row, writes 27/251 planted names),
an unconditional majority vote on numbers (changed 0 on fresh; its one change on the first set was a different mention). The shipped rule needs BOTH others to agree.

## Service surface (harness/service.py)

- POST /api/jobs (file, user, contacts, lang) and POST /api/jobs/sample -> {id}; GET /api/jobs/{id} to poll.
  Stages queued -> listening -> searching -> checking -> summarising -> done. Job holds segments
  (witness texts, view word lists, edits with why/heard), questions [{id,kind who|word|number|name,
  key, at_s (estimated), options, heard, answer}], deal_sheet, timing, to_confirm, unsure_people.
- POST /api/jobs/{id}/answers {question, value} settles a number/word on that job.
- GET /api/jobs/{id}/audio. Finished calls are saved to data/calls/<user>/<id>.json and survive restart;
  GET /api/users/{user}/calls lists them.
- GET/POST /api/users/{user}/memory, /names {name, action confirm|reject|forget}, /names/import {names}
  (contact list, names only, max 300), DELETE /api/users/{user}.
- POST /speech-to-text: one clip <= 30 s, Sarvam-shaped request/response. Form fields: names, user,
  transcript (caller's own base), stream (draft line then verified line, NDJSON), budget_ms.
  Header api-subscription-key: a Parakh key (POST /api/keys, 10 free minutes) or the access code.
  Answer: Sarvam fields + "parakh": base, formatted, edits[{from,to,why,heard}], unsure, clear (bool),
  confirm [{kind,heard,options}], recognisers, left_out, extra_listens, timing_ms, replayed, cost_to_run_inr.
- GET /api/keys/{key}, GET /api/stats, GET /api/scoreboard, GET /api/health, GET /docs.
- Uploads are deleted after 24 h; logs hold sizes/times/costs, never text.

## Numbers that are true today (data/scoreboard.json; rebuild with scripts/build_scoreboard.py)

Fresh set = FLEURS Hindi test split, 189 recordings, 313 name mentions, 196-name list, no sentence in
common with the first set, run once after the rules were frozen.

| | model alone | with Parakh | note |
|---|---|---|---|
| Saaras v3 | 89.1% | 95.8% | 21 fixed, 0 lost |
| Saaras v4 | 91.1% | 96.5% | 17 fixed, 0 lost, p < 0.0001 |
| gpt-transcribe | 90.7% | 96.8% | 19 fixed, 0 lost |
| recordings with every name right (v4) | 85.7% | 94.7% | |
| WER (v4) | 4.6% | 3.5% | lowest of any system tested |
| names confirmed once, next time (loop sim) | 93.1% | 96.7% | first-time names unchanged 89.8% |

Keyword features on the same set: Sarvam v4 + its 50 keyterms 97.1% (own names first) / 95.2% (A-Z);
OpenAI + 100 keywords 95.8%. Versus Parakh all within chance (p 0.39-0.73). Planted sound-alikes
written (of 251): OpenAI keywords 2, Parakh 6, Sarvam A-Z 12, Sarvam planted-first 35.
First set (91 rec.): v4 89.3 -> 96.4; phone-line audio (8 kHz mu-law) 86.4 -> 94.3; no context
89.3 -> 90.7 (ns); IndicContextEval: tie (82.0 vs 82.3). Three private trade calls: 14/14 confirmed
mentions (rules were developed on them; not held out). Speed, 40 fresh clips: draft 0.87 s, checked
1.80 s median; 24/40 needed no second listen. Cost to run ~Rs 1.4/min at list prices.

Numbers right (scripts/numbers_table.py, runs/numbers.json): fresh 77/80 base and Parakh alike.

Caveats to keep stating: two rules changed after seeing first-set results (rival spellings in the
transcript's script; confirmed names not re-asked), the fresh set was run after both. An earlier
claim that OpenAI's keyword feature wrote 19/119 planted names was an artefact of list order
(planted names first); alphabetical gives 0. Number-doubt is unproven (one flag on the calls).
Play-button timing is estimated from word position (no word timestamps from the APIs).

## Decisions the user made

- Name: Parakh (Sunwai rejected). Idea text kept broad: "trust layer for voice AI".
- No git commits unless asked. Use API credits carefully; say costs before fresh runs.
- Demo hosting: tunnel from the laptop with an access code (AWS chosen first, never configured).
- Slides: own look (ivory/serif), not the account's design system.
- Page: the six-screen ivory version is the one to keep; a dark rebuild was rejected
  ("previous design was good"); it is kept as web/index-dark.html (has a three-step try-it flow
  worth porting). Headline now: "Names and numbers, checked before you act on them."

## Open before 14:00 Sunday

1. Microphone path and phone layout: never tested by me on a real device.
2. Repo: must be committed and pushed for submission (user to say when).
3. Headline wording; optional guided three-step "try it" flow (a working draft exists in web/index-dark.html).
4. Hindi strings need a native read.
5. Sarvam data retention should be set to 0 days in their console; rotate all three API keys after the event.
6. Backup demo video in case the tunnel or an API fails during judging.
