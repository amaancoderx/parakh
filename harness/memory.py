"""What Parakh knows about one user's world, in two tiers.

    verified    names the user confirmed (or typed in). Trusted like contacts.
    candidates  names Parakh heard and checked against the audio, waiting for a yes.
                Used only as suggestions that still need a recogniser to back them.

A name becomes verified when a person adds it or says yes to it, or, once a day, when the
audio itself has backed it in AUTO_TRUST_AFTER separate recordings (see learn_daily in
service.py). Nothing a single transcript or a model writes can make a name verified:
systems that learned from one sighting learned false equivalences, and memory written from
model output can be poisoned. Auto-trusted names are marked as such and can be undone.

Also kept per user: settings (memory on or off), sources (each file the user fed in and the
names it gave), heard_as (how the recognisers misheard each name, from the fixes made) and a
log of what each daily learning run did.

Stored as JSON under data/memory/<user>.json.

    uv run python -m harness.memory dad                    # show
    uv run python -m harness.memory dad confirm "Arizona Bianco"
    uv run python -m harness.memory dad reject "HDFC Bank"
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from harness.data import ROOT

MEMORY_DIR = ROOT / "data" / "memory"
# Names searched per call, most recently used first. They are searched by sound here and at most eight
# reach a recogniser as hints, so this is not a keyword-list limit; it is the size the accuracy tests
# stop saying anything about (they used lists of 100).
MAX_VERIFIED_HINTS = 300
AUTO_TRUST_AFTER = 3  # separate recordings in which the audio backed a name before it is trusted without a tap
DEFAULT_SETTINGS = {"enabled": True, "auto_learn": True}


def path(user: str) -> Path:
    return MEMORY_DIR / f"{user}.json"


def load(user: str) -> dict[str, dict]:
    p = path(user)
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    if data and not {"verified", "candidates", "rejected"} & set(data):  # first format: a flat name map
        data = {"candidates": data}
    return {"verified": data.get("verified", {}), "candidates": data.get("candidates", {}), "rejected": data.get("rejected", {}),
            "settings": {**DEFAULT_SETTINGS, **data.get("settings", {})}, "sources": data.get("sources", {}),
            "log": data.get("log", [])}


def _save(user: str, memory: dict[str, dict]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path(user).write_text(json.dumps(memory, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def enabled(user: str) -> bool:
    return bool(user) and load(user)["settings"]["enabled"]


def settings(user: str, **changes) -> dict:
    memory = load(user)
    memory["settings"].update({k: bool(v) for k, v in changes.items() if k in DEFAULT_SETTINGS and v is not None})
    _save(user, memory)
    return memory["settings"]


def verified(user: str) -> list[str]:
    """Verified names, most recently used first, at most MAX_VERIFIED_HINTS."""
    v = load(user)["verified"]
    return sorted(v, key=lambda n: -v[n].get("last_used", 0))[:MAX_VERIFIED_HINTS]


def candidates(user: str) -> list[str]:
    return list(load(user)["candidates"])


def propose(user: str, names: dict[str, dict]) -> list[str]:
    """Record names heard and backed by the audio as candidates. Returns the ones that are new."""
    memory = load(user)
    new = []
    for name, evidence in names.items():
        if name in memory["verified"] or name in memory["rejected"]:
            continue
        entry = memory["candidates"].setdefault(name, {"first_seen": time.time(), "seen": 0, "evidence": [], "heard_in": []})
        where = evidence.get("call") or evidence.get("from", "")
        if where in entry.setdefault("heard_in", []):
            continue  # the same recording checked again is not a second hearing
        entry["heard_in"] = (entry["heard_in"] + [where])[-20:]
        entry["seen"] = len(entry["heard_in"])
        entry["evidence"] = (entry["evidence"] + [evidence])[-5:]
        if entry["seen"] == 1:
            new.append(name)
    _save(user, memory)
    return new


def confirm(user: str, name: str, how: str = "confirmed by the user") -> None:
    memory = load(user)
    entry = memory["candidates"].pop(name, {})
    memory["rejected"].pop(name, None)
    memory["verified"][name] = {**entry, "verified": how, "verified_at": time.time(), "last_used": time.time()}
    _save(user, memory)


def confirm_many(user: str, names: list[str], how: str = "from the user's contacts", source: str = "") -> int:
    """Verify a whole list in one write. Returns how many were new."""
    memory = load(user)
    new = 0
    for name in names:
        if name in memory["verified"]:
            continue
        entry = memory["candidates"].pop(name, {})
        memory["rejected"].pop(name, None)
        memory["verified"][name] = {**entry, "verified": how, "verified_at": time.time(), "last_used": time.time(),
                                    **({"source": source} if source else {})}
        new += 1
    _save(user, memory)
    return new


def add_source(user: str, source_id: str, info: dict) -> None:
    memory = load(user)
    memory["sources"][source_id] = {**memory["sources"].get(source_id, {}), **info}
    _save(user, memory)


def drop_source(user: str, source_id: str) -> int:
    """Forget a file the user fed in, and the names that came only from it. Returns how many names went."""
    memory = load(user)
    memory["sources"].pop(source_id, None)
    gone = [n for n, e in memory["verified"].items() if e.get("source") == source_id]
    for n in gone:
        memory["verified"].pop(n)
    _save(user, memory)
    return len(gone)


def heard_as(user: str, fixes: dict[str, str]) -> None:
    """Remember how the recognisers misheard each known name: {"Eicher": "Aishar"}."""
    memory = load(user)
    changed = False
    for name, said in fixes.items():
        entry = memory["verified"].get(name) or memory["candidates"].get(name)
        if entry is not None and said and said.lower() != name.lower() and said not in entry.get("heard_as", []):
            entry["heard_as"] = (entry.get("heard_as", []) + [said])[-8:]
            changed = True
    if changed:
        _save(user, memory)


def auto_trust(user: str) -> list[str]:
    """Trust names the audio backed in AUTO_TRUST_AFTER separate recordings. Returns the names promoted."""
    memory = load(user)
    ready = [n for n, e in memory["candidates"].items() if e.get("seen", 0) >= AUTO_TRUST_AFTER]
    for name in ready:
        entry = memory["candidates"].pop(name)
        memory["verified"][name] = {**entry, "verified": f"heard and backed in {entry['seen']} separate recordings",
                                    "auto": True, "verified_at": time.time(), "last_used": time.time()}
    if ready:
        _save(user, memory)
    return ready


def write_log(user: str, entry: dict) -> None:
    memory = load(user)
    memory["log"] = ([entry] + memory["log"])[:30]
    _save(user, memory)


def reject(user: str, name: str) -> None:
    memory = load(user)
    memory["candidates"].pop(name, None)
    memory["verified"].pop(name, None)
    memory["rejected"][name] = {"rejected_at": time.time()}
    _save(user, memory)


def drop(user: str, name: str) -> None:
    """Remove a name without marking it as wrong."""
    memory = load(user)
    for tier in ("verified", "candidates", "rejected"):
        memory[tier].pop(name, None)
    _save(user, memory)


def touch(user: str, names: list[str]) -> None:
    """Mark verified names as used, so the per-call hint list keeps the recent ones."""
    memory = load(user)
    hit = [n for n in names if n in memory["verified"]]
    for n in hit:
        memory["verified"][n]["last_used"] = time.time()
    if hit:
        _save(user, memory)


def forget(user: str) -> None:
    path(user).unlink(missing_ok=True)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    user = sys.argv[1]
    if len(sys.argv) >= 4 and sys.argv[2] in ("confirm", "reject"):
        (confirm if sys.argv[2] == "confirm" else reject)(user, sys.argv[3])
    memory = load(user)
    for tier in ("verified", "candidates", "rejected"):
        print(f"{tier}: {sorted(memory[tier]) or '-'}")


if __name__ == "__main__":
    main()
