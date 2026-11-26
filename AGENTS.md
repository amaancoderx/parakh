# AGENTS.md: set up, run and test Parakh

Code: https://github.com/amaancoderx/parakh · Demo video: `web/demo.mp4` · Evidence of results: `docs/Parakh-Evidence.pdf`

The hosted demo (tryparakh.duckdns.org) ran on AWS during Equal AI Builders '26 and has been taken down.
Run it locally with the steps below: it works without any keys.

Parakh is a verification layer for Indian speech-to-text. Three speech models hear the same audio; Parakh finds
the words they disagree on, checks those against the audio and the caller's memory of names, fixes what the
audio proves, and asks about the rest. It is one Python service (FastAPI) that also serves the web app.

---

## 1. Prerequisites

| Tool | Version | Why |
|---|---|---|
| Python | 3.11 (3.10 or newer works) | the service |
| uv | 0.8 or newer (`pip install uv`, or `curl -LsSf https://astral.sh/uv/install.sh \| sh`) | installs and runs everything |
| ffmpeg | any recent build, on PATH | converts uploaded audio and splits long calls |
| A browser | any recent Chrome, Edge or Firefox | the web app |

No database, no Node, no Docker. Everything is stored as files under `data/`.

## 2. Environment variables and keys

Copy `.env.example` to `.env`. Every variable:

| Variable | Needed for | Without it |
|---|---|---|
| `OPENAI_API_KEY` | new audio (gpt-transcribe), the call summary, name lookup, how a new name is said | the bundled recordings still work (replayed); new audio fails with a clear message |
| `SARVAM_API_KEY` | new audio (Saaras v3 and v4) | same as above |
| `PARAKH_ACCESS_CODE` | optional. If set, new audio and new API keys need this code | leave empty: open to anyone |
| `ELEVENLABS_API_KEY`, `DEEPGRAM_API_KEY`, `DEEPGRAM_MODEL` | optional, research comparisons only | not used by the app |

### No-key mode (works out of the box)

**The app runs fully without any key.** The answers of all three speech models and the text models for the bundled
recordings are saved in `.cache/`, so with an empty `.env`:

- both sample calls on **Check a call** run end to end (listen, check, questions, summary),
- **Developers → Run it here** and **Compare without and with memory** work (they use `web/sample-turn.wav`, a real call clip),
- **Memory**: uploading a contacts/ledger file (.csv .xlsx .vcf .txt), confirming names and **Run now** all work,
- the API (`/speech-to-text`) works on `web/sample-turn.wav` with a key you create in the app.

Only **brand-new audio** (recording your own voice, uploading your own file) needs `OPENAI_API_KEY` and
`SARVAM_API_KEY`. Without them it shows: "SARVAM_API_KEY is not set: only the bundled recordings replay without it".
To test new audio, add both keys to `.env` and restart.

## 3. Install, seed and start

```bash
cd parakh                      # the folder that holds this file
cp .env.example .env           # optional: add keys for new audio
uv sync                        # installs Python 3.11 if needed and every dependency (about 30 s)
uv run uvicorn harness.service:app --host 0.0.0.0 --port 8000
```

That is the only process. There is nothing to seed: the bundled calls (`data/samples/`), saved model answers
(`.cache/`) and results (`data/scoreboard.json`, `runs/`) ship in the zip. User data is created on first use.

Check it is up:

```bash
curl http://localhost:8000/api/health
# {"ok":true,"recognisers":["Saaras v4","Saaras v3","gpt-transcribe"]}
```

Tests (no network, no keys): `uv run pytest` → 78 passed.

## 4. URLs and ports

Everything is on **port 8000**.

| URL | What |
|---|---|
| http://localhost:8000/ | landing page |
| http://localhost:8000/#/app | the app: Check a call |
| http://localhost:8000/#/app/calls | saved calls |
| http://localhost:8000/#/app/names | Memory |
| http://localhost:8000/#/app/results | measured results |
| http://localhost:8000/#/app/developers | API keys, quickstart, live API try-out |
| http://localhost:8000/#/app/reference | API reference |
| http://localhost:8000/docs | interactive API explorer (Swagger) |
| http://localhost:8000/api/health | health check |

## 5. Logins and user types

There is **no sign-in, on purpose**: anyone can try it at once. Two kinds of user:

| User | How they get in | What separates them |
|---|---|---|
| **Trader** (the app) | open `/#/app` | each browser gets its own private workspace id (shown bottom-left, e.g. `ID u-k0i74p5u`). A new private window is a new user. |
| **Developer** (the API) | create an API key on `/#/app/developers` (name it, copy it) | the key, sent as the `api-subscription-key` header. Each key has 10 free minutes of audio. |

A test API key can also be made without the UI:

```bash
curl -X POST http://localhost:8000/api/keys -H "Content-Type: application/json" -d '{"label":"Agent test","user":"u-agent"}'
# → {"key":"pk_...", "id":"...", "minutes_left":10, ...}   the full key is returned only here
```

## 6. Journeys to test end to end

### A. Trader checks a real call (no keys needed)
1. Open http://localhost:8000/#/app.
2. Under **Real trade calls**, click **Steel drums order** (a real 3.5-minute Hinglish call).
3. Watch the four steps finish: Listening with 3 models → Finding likely names → Checking against the audio → Writing the summary.
4. Expect **What was agreed** (a short deal sheet) and questions to confirm, each with a play button for the seconds around the word.
5. Answer a question with one tap (for example **Mohammad bhai**). It is saved with the call.
6. Scroll to **The call, word for word**: the speech model alone on the left, Parakh on the right. Click a highlighted word: a popover shows what each model heard and why Parakh chose its word. Expect **Eicher** fixed (the model wrote "Aishar"), and amounts written as digits (for example 5,600).
7. Use the **Speech model alone** dropdown to switch the left column between Saaras v4, Saaras v3 and gpt-transcribe.
8. Open **Calls** in the sidebar: the call is saved and reopens exactly as it was.

### B. Trader feeds memory and it improves calls (no keys needed)
1. Open **Memory** (`/#/app/names`). Memory and Learn every day are on.
2. Drop a contacts or ledger file on **Drop files here** (any .csv/.xlsx/.vcf/.txt with a Name or Party column; an example: a CSV with lines `Party Name,Mobile` / `Mohammad bhai,9876500001` / `Eicher,0`). Expect the names under **Sources** and in **What Parakh knows**; phone numbers are dropped.
3. Or type names in the box and press **Add**.
4. Go back to **Check a call**, run **Which tile was it?**. The tile's name, **Arizona Bianco**, is heard and appears in Memory under **Waiting for your yes** with "1 of 3 hearings". Click **Confirm**.
5. On Memory, click **Run now** (the daily learning run, which also runs on its own once a day). Expect a timeline entry: calls checked again, and any calls it improved.
6. Switch **Memory** off: a banner says nothing is used or learned. Switch it back on.
7. **Delete all my data** wipes this workspace's memory and calls.

### C. Developer uses the API (no keys needed for the sample clip)
1. Open **Developers** (`/#/app/developers`). In step 1, type a key name (for example `Production`) and click **Create key**. A dialog shows the full key once: **Copy**, then **Done**.
2. Step 3: click **Run it here**. Expect a draft from Saaras v4 with **"Aishar"**, then Parakh's checked result with **Eicher**, the evidence, and `clear: nothing left to confirm`.
3. Steps 2 and 3 have copy-paste commands with your key filled in, as cURL (macOS/Linux or Windows PowerShell), Python or Node.js. From a terminal:
   ```bash
   curl -o turn.wav http://localhost:8000/static/sample-turn.wav
   curl -N http://localhost:8000/speech-to-text -H "api-subscription-key: YOUR_KEY" \
     -F file=@turn.wav -F names="Eicher, Mohammad bhai" -F stream=true
   ```
   Two JSON lines come back: `"event": "draft"` then `"event": "verified"` with `parakh.edits` `[{"from": "Aishar", "to": "Eicher", ...}]`.
4. **Memory for your app**: click **Compare without and with memory**. Left: memory empty, no names sent, still "Aishar". Right: after a contacts file is uploaded to that user's memory, no names sent, **Eicher**, with `"fixed_from_memory": ["Eicher"]`.
   By hand: `curl http://localhost:8000/v1/memory/sources -H "api-subscription-key: YOUR_KEY" -F user=amit -F file=@contacts.csv`, then the speech-to-text call above with `-F user=amit` and without `names`.
5. **API keys** card: the key shows its usage; **Revoke** it, then repeat the curl: expect `401 Missing or revoked API key`.
6. **API reference** (`/#/app/reference`): every endpoint, field, response and error code.

### D. Results
Open **Results** (`/#/app/results`) and the landing page: every number is read from `data/scoreboard.json`
(built from `runs/`). The memory comparison is reproduced with `uv run python scripts/memory_eval.py calls`
(the public-recording part needs the FLEURS audio, not in the zip; see README "Reproduce the results").

## 7. What is simulated, mocked or not finished

- **Replayed, not mocked:** the two sample calls and `web/sample-turn.wav` are real trader recordings (recorded with consent). Their model answers are replayed from `.cache/`, so they are instant and free; the page says "replayed from saved model answers". New audio is processed live.
- **Scripted timing:** the "trader's week" result (Memory page, README) runs the real calls through the real pipeline, with days and nights back to back and the one "yes" tap made by `scripts/memory_eval.py`.
- **Made for the test:** the party ledger in that test, with decoy names. The phone-line test passes real recordings through a phone codec instead of dialling.
- **Not built:** sign-in (each browser is a workspace; developers use API keys), payments (keys get 10 free minutes), phone-number OTP login, live phone-call integration (audio is uploaded or recorded in the browser), word-level timestamps (question times are estimates).
- **Limits:** one API clip is up to 30 s; an uploaded call up to 6 minutes and 12 MB. Uploaded audio is deleted after a week.

## 8. Where things are

| Path | What |
|---|---|
| `harness/service.py` | the web service and every API route |
| `harness/parakh.py` | the checking engine (listen, doubt, check, decide) |
| `harness/memory.py`, `harness/sources.py` | memory, and reading names from files |
| `harness/numbers.py` | spoken Hindi numbers to digits |
| `web/index.html` | the whole front end |
| `data/samples/`, `.cache/` | bundled calls and saved model answers (the no-key mode) |
| `data/scoreboard.json`, `runs/` | measured results |
| `tests/` | 78 tests, no network |
| `deploy/` | AWS deployment scripts (`deploy/aws.sh`) |
