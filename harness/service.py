"""Parakh as a web service: the API and the demo page.

    uv run uvicorn harness.service:app --port 8000

    POST /api/jobs                 audio file (+ user, contacts)  -> {"id"}       starts a job
    POST /api/jobs/sample          {"sample", "user", "contacts"} -> {"id"}       same, on a bundled recording
    GET  /api/jobs/{id}            progress and result; poll until status is "done"
    GET  /api/jobs/{id}/audio      the recording, for playback
    GET  /api/samples              bundled recordings
    GET  /api/users/{user}/memory  verified names and names waiting for a yes
    POST /api/users/{user}/names   {"name", "action": "confirm" | "reject" | "forget"}
    POST /api/users/{user}/names/import   {"names": [...]}  a contact list, names only
    POST /api/jobs/{id}/answers    {"question", "value"}    settle a doubted number or word on this recording
    DELETE /api/users/{user}       forget everything about this user
    GET  /api/scoreboard           measured results on held-out public data and real calls
    GET  /api/users/{user}/calls   that person's finished calls, newest first; each reopens by its id
    POST /api/keys                 {"label", "user"} -> a named key with a free allowance, for /speech-to-text
    GET  /api/users/{user}/keys    that workspace's keys, masked, with usage
    DELETE /api/users/{user}/keys/{id}  revoke a key
    GET  /api/keys/{key}           minutes used and left, and what they cost to run
    GET  /api/stats                requests, audio minutes and running cost so far
    POST /speech-to-text           one short clip, answered at once. Same request and response shape as
                                   Sarvam's endpoint of that name, plus `names`, `user`, `transcript`,
                                   `stream` and `budget_ms`; the checks come back under "parakh".

A job moves through: listening (every recogniser, text shown at once) -> searching (topic and
real-world names, calls only) -> checking (names against the audio) -> summarising (deal sheet)
-> done. The page shows the base transcript as soon as it exists and patches corrections in.

Fresh audio costs API credits, so POST /api/jobs needs the X-Access-Code header when the
PARAKH_ACCESS_CODE environment variable is set.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
import wave
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from harness import account, memory
from harness.context import ContextIndex, common_word_keys
from harness.data import ROOT
from harness.dealsheet import deal_sheet
from harness.discover import discover
from harness.numbers import to_digits
from harness.parakh import Config, _roman_title, listen, run
from harness.phonetic import is_devanagari, same_sound
from harness.render import _short, view, why
from harness.segment import MAX_SECONDS, duration, split
from harness.systems import available_systems

WEB_DIR = ROOT / "web"
SAMPLES_DIR = ROOT / "data" / "samples"
UPLOADS_DIR = ROOT / "data" / "uploads"
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_SECONDS_TOTAL = 6 * 60
MAX_SECONDS_LIVE = 30  # /speech-to-text takes one short clip, like the Sarvam endpoint it mirrors

@asynccontextmanager
async def lifespan(_: FastAPI):
    warm_up()
    yield


app = FastAPI(title="Parakh", description="The verification layer between speech models and the actions taken on what they hear.",
              lifespan=lifespan)
JOBS: dict[str, dict] = {}
_systems = None


def systems() -> dict:
    global _systems
    if _systems is None:
        _systems = available_systems()
    return _systems


KEEP_UPLOADS_S = 24 * 3600  # uploaded audio is deleted a day after it arrives; the checked text of the call stays


def _sweep_uploads() -> None:
    """Delete uploaded recordings older than a day, now and then every hour."""
    while True:
        try:
            for folder in UPLOADS_DIR.iterdir() if UPLOADS_DIR.exists() else []:
                if folder.is_dir() and folder.name != "latency" and time.time() - folder.stat().st_mtime > KEEP_UPLOADS_S:
                    shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass
        time.sleep(3600)


def warm_up() -> None:
    """Load the word list, the transliteration tables and the recogniser adapters before the first request."""
    common_word_keys()
    same_sound("नमस्ते", "namaste")
    systems()
    threading.Thread(target=_sweep_uploads, daemon=True).start()


def _user(user: str | None) -> str:
    u = re.sub(r"[^a-z0-9_-]", "", (user or "guest").lower())[:40]
    return u or "guest"


def _names(text: str | None) -> list[str]:
    return [n.strip() for n in re.split(r"[\n,;]+", text or "") if n.strip()][:60]


def _public(job: dict) -> dict:
    return {k: v for k, v in job.items() if not k.startswith("_")}


def _work(job: dict) -> None:
    cfg = Config()
    S = systems()
    t0 = time.perf_counter()
    try:
        segments: list[Path] = job["_segments"]
        user, typed = job["_user"], job["_contacts"]

        # 1. Listen: every recogniser, no hints. The page shows this text straight away.
        job["status"] = "listening"
        heard_all, replayed, first_run = [], True, 0.0
        for n, seg in enumerate(segments):
            heard, failed = listen(seg, cfg, S)
            heard_all.append(heard)
            replayed = replayed and all(h.get("cached") for h in heard.values())
            base = cfg.base if cfg.base in heard else next(iter(heard))
            job["failed"] = sorted(set(job["failed"]) | {f.split(":")[0] for f in failed})
            job["segments"][n].update(
                stage="heard", base_name=_short(base),
                witnesses=[{"name": _short(w), "text": h["text"].replace("\n", " ")} for w, h in heard.items()],
                view={"base": [{"t": t, "c": ""} for t in heard[base]["text"].split()], "parakh": []},
            )
        job["timing"]["heard_s"] = round(time.perf_counter() - t0, 1)

        # 2. Search: for a call, work out the topic and which real names the garbled words could be.
        found = {"topic": "", "candidates": [], "people": []}
        if job["_discover"]:
            job["status"] = "searching"
            found = discover([{w: h["text"].replace("\n", " ") for w, h in heard.items()} for heard in heard_all])
            job["topic"] = found["topic"]

        # 3. Check: a name is written only if the audio backs it.
        job["status"] = "checking"
        trusted = [*typed, *memory.verified(user)]
        index = ContextIndex.build({"contacts": trusted, "found": [*memory.candidates(user), *found["candidates"]]})
        heard_and_backed: dict[str, dict] = {}
        traces = []
        everything = [h["text"] for heard in heard_all for h in heard.values()]
        for n, (seg, heard) in enumerate(zip(segments, heard_all)):
            r = run(seg, index, cfg, S, heard=heard, nearby=everything)  # arithmetic said anywhere in the call counts
            t = r["trace"]
            traces.append(t)
            for name in t.get("found", []):
                heard_and_backed[name] = {"from": job["title"], "evidence": "a recogniser wrote it unprompted and another backed it"}
            base_text = t["witnesses"][t["base"]]
            job["segments"][n].update(
                stage="checked",
                view=view(base_text, t, set(trusted)),
                text=r["text"].replace("\n", " "),
                dictated=to_digits(r["text"].replace("\n", " ")),
                edits=[{"from": e["from"], "to": e["to"], "why": why(e, t, set(trusted))} for e in t.get("edits", [])],
                suggested=t.get("suggested", []),
                unresolved=t.get("unresolved", []),
                unsure=[{"text": u.get("value", u["text"]), "heard": {_short(w): x for w, x in u["heard"].items()}}
                        for u in [*t.get("unsure_spans", []), *t.get("number_doubts", [])]],
                extra_passes=t.get("extra_passes", 0),
                latency_s=r["latency_s"],
            )
            first_run += r["latency_s"]
        job["to_confirm"] = [n for n in heard_and_backed if n not in trusted]
        memory.propose(user, {n: heard_and_backed[n] for n in job["to_confirm"]})
        memory.touch(user, [e["to"] for s in job["segments"] for e in s.get("edits", [])])
        settled = [e["to"] for s in job["segments"] for e in s.get("edits", [])]
        people = [[v.strip() for h in ([p["heard"]] if isinstance(p["heard"], str) else p["heard"]) for v in str(h).split(" / ")]
                  for p in found.get("people", [])]
        settled += trusted  # a name the user has confirmed answers the question of who it was
        job["unsure_people"] = [p for p in people if not any(same_sound(h, s, strict_final=True) for h in p for s in settled)]
        # Show each disputed person's name as a question on the word itself, wherever the base wrote it.
        for n, t in enumerate(traces):
            base_toks = [w.strip(".,!?;:।") for w in t["witnesses"][t["base"]].split()]
            taken = [tuple(x["span"]) for k in ("edits", "unsure_spans", "number_doubts") for x in t.get(k, [])]
            added = False
            for group in job["unsure_people"]:
                for option in group:
                    words = option.split()
                    for i in range(len(base_toks) - len(words) + 1):
                        if [w.lower() for w in base_toks[i : i + len(words)]] == [w.lower() for w in words] and not any(
                            a < i + len(words) and i < b for a, b in taken
                        ):
                            t.setdefault("unsure_spans", []).append(
                                {"span": (i, i + len(words)), "name": (i, i + len(words)), "text": option, "heard": {}, "options": group})
                            taken.append((i, i + len(words)))
                            added = True
        # Everything that needs a yes, as plain questions, each with roughly when it is said in the recording.
        questions: list[dict] = []
        asked: set = set()
        for n, t in enumerate(traces):
            seg, base_text = job["segments"][n], t["witnesses"][t["base"]]

            def ask(kind: str, key, word: int, payload: dict | None = None, **fields) -> None:
                if key in asked:  # one question per name, however often it is said
                    if payload is not None:
                        payload["q"] = next(q["id"] for q in questions if q["key"] == str(key))
                    return
                asked.add(key)
                questions.append({"id": len(questions), "kind": kind, "key": str(key), "seg": n,
                                  "at_s": _when(base_text, word, seg["start_s"], seg["seconds"]), "answer": None, **fields})
                if payload is not None:
                    payload["q"] = questions[-1]["id"]

            roman = not is_devanagari(base_text)
            for u in t.get("unsure_spans", []):
                group = u.get("options") or next((g for g in job["unsure_people"] if any(same_sound(o, u["text"], strict_final=True) for o in g)), None)
                if group:
                    u["options"] = group
                    ask("who", ("who", *group), u["span"][0], u, options=group)
                else:
                    heard = {_short(t["base"]): u["text"], **{_short(w): x for w, x in u["heard"].items()}}
                    options = [_roman_title(x) if roman and is_devanagari(x) else x for x in heard.values() if x]
                    ask("word", ("word", u["text"].lower()), u["span"][0], u, text=u["text"], heard=heard,
                        options=list(dict.fromkeys(options)))
            for d in t.get("number_doubts", []):
                ask("number", ("number", n, d["span"][0]), d["span"][0], d, text=d["text"], options=d["options"],
                    heard={_short(t["base"]): d["text"], **{_short(w): x for w, x in d["heard"].items()}})
            for e in t.get("edits", []):
                if e["to"] in job["to_confirm"]:
                    ask("name", ("name", e["to"]), e["span"][0], name=e["to"], heard_as=e["from"])
            job["segments"][n]["view"] = view(base_text, t, set(trusted))
        job["questions"] = questions
        job["timing"]["checked_s"] = round(time.perf_counter() - t0, 1)
        # Bundled recordings replay saved recogniser responses; report what the recognisers took originally.
        job["timing"]["replayed"] = replayed
        job["timing"]["recogniser_s"] = round(first_run, 1)
        job["extra_passes"] = sum(s.get("extra_passes", 0) for s in job["segments"])

        # 4. Summarise: the deal sheet, for calls.
        if job["_discover"]:
            job["status"] = "summarising"
            unsure = {u["text"] for s in job["segments"] for u in s.get("unsure", [])}
            unsure |= {name for group in job["unsure_people"] for name in group}
            transcript = " ".join(s["dictated"] for s in job["segments"])
            for u in unsure:
                transcript = transcript.replace(u, f"{u} [?]")
            job["deal_sheet"] = deal_sheet(transcript, job["_lang"])
        job["timing"]["total_s"] = round(time.perf_counter() - t0, 1)
        job["status"] = "done"
        account.save_call(user, _public(job), job["_audio"])
        calls = len(segments) * (1 if job["timing"]["replayed"] else 2)
        account.log("/api/jobs", user, job["seconds"], round(1000 * (time.perf_counter() - t0)),
                    0.0 if job["timing"]["replayed"] else account.cost_inr(job["seconds"], 2, 1 + job["extra_passes"] / max(1, len(segments))),
                    replayed=job["timing"]["replayed"], segments=len(segments), extra_listens=job["extra_passes"], recogniser_calls=calls)
    except Exception as e:  # shown on the page; the job never hangs
        job["status"] = "error"
        job["error"] = f"{type(e).__name__}: {e}"[:400]


def _when(base_text: str, word: int, start_s: float, seconds: float) -> float:
    """Roughly when a word is said: its share of the segment's letters. The recognisers give no word times."""
    toks = base_text.split()
    before, total = sum(len(t) + 1 for t in toks[:word]), max(1, sum(len(t) + 1 for t in toks))
    return round(start_s + seconds * before / total, 1)


def _start(title: str, audio: Path, segments: list[Path], user: str, contacts: list[str], discover_names: bool,
           lang: str = "en") -> dict:
    job_id = uuid.uuid4().hex[:12]
    lengths = [_wav_seconds(s) for s in segments]
    job = {
        "id": job_id, "title": title, "status": "queued", "error": None, "topic": "", "failed": [],
        "segments": [{"seg": s.stem, "stage": "queued", "start_s": round(sum(lengths[:n]), 2), "seconds": round(lengths[n], 2)}
                     for n, s in enumerate(segments)],
        "to_confirm": [], "unsure_people": [], "questions": [], "deal_sheet": None, "timing": {}, "extra_passes": 0,
        "seconds": round(sum(lengths), 1),
        "_audio": audio, "_segments": segments, "_user": user, "_contacts": contacts, "_discover": discover_names,
        "_lang": "hi" if lang == "hi" else "en",
    }
    JOBS[job_id] = job
    threading.Thread(target=_work, args=(job,), daemon=True).start()
    return {"id": job_id}


def _check_code(*given: str | None) -> None:
    code = os.getenv("PARAKH_ACCESS_CODE")
    if code and code not in given:
        raise HTTPException(401, "This demo needs an access code to process new audio.")


def _is_plain_wav(path: Path) -> bool:
    try:
        with wave.open(str(path)) as w:
            return (w.getnchannels(), w.getframerate(), w.getsampwidth()) == (1, 16000, 2)
    except (wave.Error, EOFError):
        return False


def _wav_seconds(path: Path) -> float:
    """Length from the wav header: no ffprobe process on the way to the recognisers."""
    try:
        with wave.open(str(path)) as w:
            return w.getnframes() / w.getframerate()
    except (wave.Error, EOFError):
        return duration(path)


async def _ingest(file: UploadFile, limit_s: float) -> tuple[Path, Path, float]:
    """Save an upload as 16 kHz mono. Returns (its folder, the wav, its length in seconds)."""
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Recording is too large (12 MB limit).")
    job_dir = UPLOADS_DIR / uuid.uuid4().hex[:12]
    job_dir.mkdir(parents=True, exist_ok=True)
    raw = job_dir / ("input" + (Path(file.filename or "").suffix.lower() or ".webm"))
    raw.write_bytes(data)
    wav = job_dir / "audio.wav"
    if _is_plain_wav(raw):  # already 16 kHz mono 16-bit: use it as it is, no conversion
        wav = raw
    else:
        done = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-ac", "1", "-ar", "16000", str(wav)],
                              capture_output=True, text=True)
        if done.returncode != 0 or not wav.exists():
            raise HTTPException(400, "Could not read that audio file.")
    seconds = _wav_seconds(wav)
    if seconds < 0.4:
        raise HTTPException(400, "The recording is empty.")
    if seconds > limit_s:
        raise HTTPException(413, f"Recording is too long ({limit_s:.0f} second limit here).")
    return job_dir, wav, seconds


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    user: str = Form("guest"),
    contacts: str = Form(""),
    lang: str = Form("en"),
    x_access_code: str | None = Header(default=None),
):
    _check_code(x_access_code)
    job_dir, wav, seconds = await _ingest(file, MAX_SECONDS_TOTAL)
    segments = [wav] if seconds <= MAX_SECONDS else split(wav, job_dir / "segments")
    return _start(file.filename or "Your recording", wav, segments, _user(user), _names(contacts), discover_names=seconds > 20, lang=lang)


# ---- /speech-to-text: one clip, answered at once -------------------------------------------------

SUPPLIED = "yours"  # the caller's own transcript, when they send one
STANDS_IN_FOR = "saaras-v3 translit"  # the recogniser we skip when the caller brings a transcript


def _verify(wav: Path, names: list[str], user: str, supplied: str, budget_ms: int, t0: float):
    """Yields a draft as soon as there is a base transcript, then the checked result.

    supplied: the caller's own transcript of this clip. It becomes the base, and one fewer
    recogniser is called. budget_ms: how long after the draft to wait for the other recognisers;
    one that is slower is left out (0 waits for all).
    """
    cfg, S = Config(), systems()
    request_id = uuid.uuid4().hex

    def ms() -> int:
        return round(1000 * (time.perf_counter() - t0))

    trusted = [*names, *(memory.verified(user) if user else [])]
    calls = [w for w in cfg.witnesses if w in S and not (supplied and w == STANDS_IN_FOR)]
    pool = ThreadPoolExecutor(max_workers=len(calls) + 1)
    # Names are known before the audio is heard: work out how they sound while the recognisers run.
    index_job = pool.submit(ContextIndex.build, {"contacts": trusted, "found": memory.candidates(user) if user else []})
    done_at: dict[str, int] = {}

    def call(w: str) -> dict:
        r = S[w](wav)
        done_at[w] = ms()
        return r

    jobs = {pool.submit(call, w): w for w in calls}
    heard: dict[str, dict] = {}
    failed: list[str] = []
    base, draft_ms, deadline = cfg.base, None, None
    if supplied:
        heard[SUPPLIED] = {"text": supplied, "latency_s": 0.0, "cached": False}
    pending = set(jobs)
    try:
        while True:
            # The draft: the base recogniser's text, or the first one back if the base is down.
            ready = base in heard or (heard and all(jobs[f] != base for f in pending))
            if draft_ms is None and (supplied or ready):
                base = SUPPLIED if supplied else (base if base in heard else next(iter(heard)))
                draft_ms = ms()
                deadline = time.perf_counter() + budget_ms / 1000 if budget_ms > 0 else None
                yield {"event": "draft", "request_id": request_id, "transcript": heard[base]["text"].replace("\n", " "),
                       "model": _short(base), "ms": draft_ms}
            if not pending:
                break
            left = None if deadline is None else max(0.0, deadline - time.perf_counter())
            finished, pending = wait(pending, timeout=left, return_when=FIRST_COMPLETED)
            if not finished:  # the budget ran out: carry on without the slow ones
                break
            for f in finished:
                try:
                    heard[jobs[f]] = f.result()
                except Exception as e:  # rate limit, outage, credits
                    failed.append(f"{jobs[f]}: {e}")
        if draft_ms is None:
            raise RuntimeError("every recogniser failed: " + "; ".join(failed))
        heard_ms = ms()
        r = run(wav, index_job.result(), replace(cfg, base=base), S, heard=heard)
    finally:
        pool.shutdown(wait=False)
    t = r["trace"]
    text = r["text"].replace("\n", " ")
    if user:
        memory.touch(user, [e["to"] for e in t.get("edits", [])])
    replayed = all(h.get("cached") for w, h in heard.items() if w != SUPPLIED)
    yield {
        "event": "verified",
        "request_id": request_id,
        "transcript": text,
        "timestamps": None,
        "diarized_transcript": None,
        "language_code": None,
        "parakh": {
            "base": {"model": _short(base), "transcript": t["witnesses"][base].replace("\n", " ")},
            "formatted": to_digits(text),
            "edits": [{"from": e["from"], "to": e["to"], "why": why(e, t, set(trusted)),
                       "heard": {_short(w): x for w, x in e.get("heard", {}).items()}} for e in t.get("edits", [])],
            "unsure": [{"text": u["text"], "heard": {_short(w): x for w, x in u["heard"].items()}} for u in t.get("unsure_spans", [])],
            # What to settle with the speaker before acting on this clip. "clear" means nothing was left open.
            "clear": not (t.get("unsure_spans") or t.get("number_doubts") or t.get("unresolved")),
            "confirm": [{"kind": "name", "heard": u["text"], "options": list(dict.fromkeys([u["text"], *(x for x in u["heard"].values() if x)]))}
                        for u in t.get("unsure_spans", [])]
                       + [{"kind": "number", "heard": d["value"], "options": d["options"]} for d in t.get("number_doubts", [])]
                       + [{"kind": "name", "heard": "", "options": group} for group in t.get("unresolved", [])],
            "names_considered": t.get("shortlist", []),
            "recognisers": [_short(w) for w in heard],
            "left_out": [_short(jobs[f]) for f in pending] + [_short(x.split(":")[0]) for x in failed],
            "extra_listens": t.get("extra_passes", 0),
            # Wall-clock here. When "replayed" is true the recognisers' answers came from this server's
            # cache, so "first_time_ms" gives what they took when they were first asked.
            "timing_ms": {"draft": draft_ms, "heard": heard_ms, "verified": ms(),
                          "recognisers": {_short(w): at for w, at in done_at.items()}},
            "replayed": replayed,
            "first_time_ms": {"draft": round(1000 * heard[base]["latency_s"]), "verified": round(1000 * r["latency_s"])},
        },
    }


@app.post("/speech-to-text")
async def speech_to_text(
    file: UploadFile = File(...),
    model: str = Form("parakh:v1"),
    mode: str = Form("translit"),
    language_code: str = Form("unknown"),
    names: str = Form("", description="Names this caller knows: contacts, places, brands. Commas or new lines."),
    user: str = Form("", description="Optional. A user id: the names they confirmed earlier are used too."),
    transcript: str = Form("", description="Optional. What your own recogniser wrote for this clip; it becomes the base."),
    stream: bool = Form(False, description="Send the draft first, then the checked result, as JSON lines."),
    budget_ms: int = Form(0, description="How long after the draft to wait for the other recognisers. 0 waits for all."),
    api_subscription_key: str | None = Header(default=None),
    x_access_code: str | None = Header(default=None),
):
    """One clip of up to 30 seconds. The answer has Sarvam's fields, with the checks under "parakh"."""
    t0 = time.perf_counter()
    key = api_subscription_key if api_subscription_key and account.usage(api_subscription_key) else None
    if key is None:
        _check_code(api_subscription_key, x_access_code)  # no key of ours: the server's own access code, if it has one
    if mode != "translit":
        raise HTTPException(400, "This version answers in Roman script: use mode=translit.")
    _, wav, seconds = await _ingest(file, MAX_SECONDS_LIVE)
    if key and not account.has_room(key, seconds):
        raise HTTPException(402, "This key has used its free allowance of audio.")
    who = key[:10] if key else (_user(user) if user.strip() else "anonymous")

    def metered(steps):
        """Pass the steps through, then record what the request used."""
        final = None
        for step in steps:
            final = step
            yield step
        p = final["parakh"]
        sarvam = sum(1 for w in p["recognisers"] if w.startswith("Saaras"))
        cost = 0.0 if p["replayed"] else account.cost_inr(seconds, sarvam, 1 + p["extra_listens"])
        p["cost_to_run_inr"] = cost
        if key:
            account.charge(key, seconds, cost)
        account.log("/speech-to-text", who, seconds, p["timing_ms"]["verified"], cost, replayed=p["replayed"],
                    draft_ms=p["timing_ms"]["draft"], extra_listens=p["extra_listens"], edits=len(p["edits"]), clear=p["clear"])

    steps = metered(_verify(wav, _names(names), _user(user) if user.strip() else "", transcript.strip(), max(0, budget_ms), t0))
    if stream:
        return StreamingResponse((json.dumps(step, ensure_ascii=False) + "\n" for step in steps), media_type="application/x-ndjson")
    final = await run_in_threadpool(lambda: list(steps)[-1])
    return {k: v for k, v in final.items() if k != "event"}


class SampleRequest(BaseModel):
    sample: str
    user: str = "guest"
    contacts: str = ""
    lang: str = "en"


def _samples() -> list[dict]:
    index = SAMPLES_DIR / "index.json"
    return json.loads(index.read_text(encoding="utf-8")) if index.exists() else []


@app.get("/api/samples")
def list_samples():
    return _samples()


@app.post("/api/jobs/sample")
def create_sample_job(req: SampleRequest):
    meta = next((s for s in _samples() if s["id"] == req.sample), None)
    if not meta:
        raise HTTPException(404, "No such sample.")
    folder = SAMPLES_DIR / meta["id"]
    segments = sorted((folder / "segments").glob("seg*.wav"))
    return _start(meta["title"], folder / meta["audio"], segments, _user(req.user), _names(req.contacts), discover_names=True, lang=req.lang)


def _job(job_id: str) -> dict:
    """The job, from memory or, after a restart, from where it was saved when it finished."""
    if job_id not in JOBS:
        saved = account.load_call(job_id)
        if saved is None:
            raise HTTPException(404, "No such job.")
        JOBS[job_id] = {**saved["job"], "_audio": Path(saved["audio"]), "_user": saved.get("user", "")}
    return JOBS[job_id]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return _public(_job(job_id))


@app.get("/api/jobs/{job_id}/audio")
def get_audio(job_id: str):
    audio = _job(job_id)["_audio"]
    if not Path(audio).exists():
        raise HTTPException(404, "The recording is no longer stored.")
    return FileResponse(audio)


@app.get("/api/users/{user}/calls")
def calls(user: str):
    return account.list_calls(_user(user))


class Answer(BaseModel):
    question: int
    value: str


@app.post("/api/jobs/{job_id}/answers")
def answer(job_id: str, body: Answer):
    """Settle a doubted number or word on this recording: the chosen value is written where the question was."""
    job, value = _job(job_id), body.value.strip()
    q = next((q for q in job["questions"] if q["id"] == body.question), None)
    if q is None or not value:
        raise HTTPException(400, "No such question.")
    q["answer"] = value
    for seg in job["segments"]:
        for word in (seg.get("view") or {}).get("parakh", []):
            if (word.get("info") or {}).get("q") == q["id"]:
                word.update(t=value, c="num" if q["kind"] == "number" else "fix", info={"said": q.get("text", ""), "answered": True})
    if job["status"] == "done" and job.get("_user"):
        account.save_call(job["_user"], _public(job), job["_audio"])  # the answer is kept with the call
    return _public(job)


class NamesImport(BaseModel):
    names: list[str]


MAX_IMPORT = 300


@app.post("/api/users/{user}/names/import")
def import_names(user: str, body: NamesImport):
    """A contact list, display names only. Kept like names the user confirmed one by one."""
    seen, names = set(), []
    for raw in body.names:
        name = re.sub(r"\s+", " ", str(raw)).strip()
        if len(name) < 3 or len(name) > 60 or not re.search(r"[^\W\d_]", name) or name.lower() in seen:
            continue  # too short to be told apart by sound, or not a name
        seen.add(name.lower())
        names.append(name)
    names = names[:MAX_IMPORT]
    added = memory.confirm_many(_user(user), names)
    # Work out how the new names are said now, so the first recording after the import does not wait for it.
    threading.Thread(target=ContextIndex.build, args=({"contacts": names},), daemon=True).start()
    return {**get_memory(user), "added": added, "skipped": len(body.names) - len(names)}


@app.get("/api/users/{user}/memory")
def get_memory(user: str):
    m = memory.load(_user(user))
    return {"verified": sorted(m["verified"]), "candidates": sorted(m["candidates"])}


class NameAction(BaseModel):
    name: str
    action: str = "confirm"


@app.post("/api/users/{user}/names")
def name_action(user: str, body: NameAction):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Empty name.")
    actions = {"confirm": memory.confirm, "reject": memory.reject, "forget": memory.drop}
    if body.action not in actions:
        raise HTTPException(400, "Unknown action.")
    actions[body.action](_user(user), name)
    return get_memory(user)


@app.delete("/api/users/{user}")
def forget_user(user: str):
    memory.forget(_user(user))
    account.forget_calls(_user(user))
    return {"forgotten": True}


class KeyRequest(BaseModel):
    label: str = ""
    user: str = ""


@app.post("/api/keys")
def make_key(body: KeyRequest, x_access_code: str | None = Header(default=None)):
    """A key for /speech-to-text with a free allowance of audio. Needs the access code when the server has one."""
    _check_code(x_access_code)
    try:
        return account.new_key(body.label, _user(body.user) if body.user else "")
    except RuntimeError as e:
        raise HTTPException(429, str(e))


@app.get("/api/keys/{key}")
def key_usage(key: str):
    found = account.usage(key)
    if found is None:
        raise HTTPException(404, "No such key.")
    return found


@app.get("/api/users/{user}/keys")
def list_keys(user: str):
    return {"keys": account.list_keys(_user(user))}


@app.delete("/api/users/{user}/keys/{key_id}")
def revoke_key(user: str, key_id: str):
    if not account.revoke(_user(user), key_id):
        raise HTTPException(404, "No such key in this workspace.")
    return {"revoked": True}


@app.get("/api/stats")
def stats():
    return account.totals()


@app.get("/api/scoreboard")
def scoreboard():
    f = ROOT / "data" / "scoreboard.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


@app.get("/api/health")
def health():
    return {"ok": True, "recognisers": [_short(n) for n in Config().witnesses if n in systems()]}


@app.exception_handler(Exception)
async def on_error(_, exc: Exception):
    return JSONResponse({"detail": f"{type(exc).__name__}: {exc}"[:300]}, status_code=500)


@app.get("/")
def home():
    return FileResponse(WEB_DIR / "index.html")


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
