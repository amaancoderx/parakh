"""Keys, usage and saved calls: what makes the pipeline a service someone can be given access to.

    data/keys.json                 one entry per key: label, when made, audio seconds used, requests, allowance
    data/logs/requests.jsonl       one line per request: when, route, who, audio seconds, time taken, what it cost to run
    data/calls/<user>/<id>.json    every finished call, so a restart loses nothing and a person can reopen it

Costs are what the recognisers charge at their list prices, not a selling price.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from pathlib import Path

from harness.data import ROOT

KEYS = ROOT / "data" / "keys.json"
LOG = ROOT / "data" / "logs" / "requests.jsonl"
CALLS = ROOT / "data" / "calls"
FREE_SECONDS = 10 * 60  # audio a new key may send before it is refused
MAX_KEYS = 200
MAX_KEYS_EACH = 10  # live keys one workspace may hold

# List prices: Sarvam speech-to-text is Rs 30 an hour per model; gpt-transcribe is $0.0045 a minute.
SARVAM_INR_PER_MIN = 0.5
OPENAI_INR_PER_MIN = 0.0045 * 85
_lock = threading.Lock()


def cost_inr(seconds: float, sarvam_calls: int = 2, openai_calls: float = 1.0) -> float:
    """What one clip costs to check: every recogniser hears all of it, and each extra listen is one more OpenAI call."""
    return round(seconds / 60 * (sarvam_calls * SARVAM_INR_PER_MIN + openai_calls * OPENAI_INR_PER_MIN), 3)


def _keys() -> dict[str, dict]:
    return json.loads(KEYS.read_text(encoding="utf-8")) if KEYS.exists() else {}


def _save(keys: dict[str, dict]) -> None:
    KEYS.parent.mkdir(parents=True, exist_ok=True)
    KEYS.write_text(json.dumps(keys, indent=1, sort_keys=True), encoding="utf-8")


def _hint(key: str) -> str:
    return f"{key[:7]}...{key[-4:]}"


def new_key(label: str = "", owner: str = "") -> dict:
    """A new key. The full key is returned only here; afterwards it is shown as pk_xxxx...xxxx."""
    with _lock:
        keys = _keys()
        if len(keys) >= MAX_KEYS:
            raise RuntimeError("No more keys can be made on this server.")
        if owner and sum(1 for e in keys.values() if e.get("owner") == owner) >= MAX_KEYS_EACH:
            raise RuntimeError(f"A workspace can hold {MAX_KEYS_EACH} keys. Revoke one first.")
        key = "pk_" + secrets.token_hex(16)
        keys[key] = {"label": label.strip()[:40] or "Untitled key", "owner": owner, "made": time.time(), "last_used": None,
                     "seconds": 0.0, "requests": 0, "cost_inr": 0.0, "allowance_seconds": FREE_SECONDS}
        _save(keys)
    made = usage(key)
    assert made is not None
    return made


def _public(key: str, entry: dict) -> dict:
    return {"id": key[3:11], "hint": _hint(key), "label": entry["label"], "made": entry.get("made"),
            "last_used": entry.get("last_used"), "requests": entry["requests"],
            "minutes_used": round(entry["seconds"] / 60, 2),
            "minutes_left": round(max(0.0, entry["allowance_seconds"] - entry["seconds"]) / 60, 2),
            "minutes_total": round(entry["allowance_seconds"] / 60, 2), "cost_to_run_inr": round(entry["cost_inr"], 2)}


def usage(key: str) -> dict | None:
    entry = _keys().get(key)
    return None if entry is None else {"key": key, **_public(key, entry)}


def list_keys(owner: str) -> list[dict]:
    """A workspace's keys, newest first, never with the full key."""
    return sorted((_public(k, e) for k, e in _keys().items() if owner and e.get("owner") == owner),
                  key=lambda k: -(k["made"] or 0))


def revoke(owner: str, key_id: str) -> bool:
    with _lock:
        keys = _keys()
        found = [k for k, e in keys.items() if k[3:11] == key_id and owner and e.get("owner") == owner]
        for k in found:
            del keys[k]
        if found:
            _save(keys)
    return bool(found)


def has_room(key: str, seconds: float) -> bool:
    entry = _keys().get(key)
    return entry is not None and entry["seconds"] + seconds <= entry["allowance_seconds"]


def charge(key: str, seconds: float, cost: float) -> None:
    with _lock:
        keys = _keys()
        if key in keys:
            keys[key]["seconds"] += seconds
            keys[key]["requests"] += 1
            keys[key]["cost_inr"] += cost
            keys[key]["last_used"] = time.time()
            _save(keys)


def log(route: str, who: str, seconds: float, took_ms: int, cost: float, **more) -> None:
    """One line per request. No transcript text and no names: only sizes, times and costs."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = {"at": round(time.time(), 1), "route": route, "who": who, "audio_s": round(seconds, 1), "took_ms": took_ms,
            "cost_inr": cost, **more}
    with _lock, LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


def totals() -> dict:
    """What the server has done so far, from the request log."""
    rows = [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines()] if LOG.exists() else []
    took = sorted(r["took_ms"] for r in rows if r["route"] == "/speech-to-text" and not r.get("replayed"))
    return {"requests": len(rows), "audio_minutes": round(sum(r["audio_s"] for r in rows) / 60, 1),
            "cost_to_run_inr": round(sum(r["cost_inr"] for r in rows), 2),
            "median_ms_per_clip": took[len(took) // 2] if took else None}


def save_call(user: str, job: dict, audio: Path) -> None:
    folder = CALLS / user
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{job['id']}.json").write_text(
        json.dumps({"when": time.time(), "user": user, "audio": str(audio), "job": job}, ensure_ascii=False), encoding="utf-8")


def load_call(job_id: str) -> dict | None:
    """A saved call by id, whoever it belongs to: ids are random and are the only way in."""
    for file in CALLS.glob(f"*/{job_id}.json"):
        return json.loads(file.read_text(encoding="utf-8"))
    return None


def list_calls(user: str, limit: int = 20) -> list[dict]:
    out = []
    for file in (CALLS / user).glob("*.json"):
        saved = json.loads(file.read_text(encoding="utf-8"))
        job = saved["job"]
        out.append({"id": job["id"], "title": job["title"], "when": saved["when"], "seconds": job["seconds"],
                    "open": sum(1 for q in job.get("questions", []) if not q.get("answer")),
                    "about": (job.get("deal_sheet") or {}).get("summary") or job.get("topic") or ""})
    return sorted(out, key=lambda c: -c["when"])[:limit]


def forget_calls(user: str) -> None:
    for file in (CALLS / user).glob("*.json"):
        file.unlink()
