"""Turn a pipeline result into what the screen shows: two word lists with marks.

Each word list is [{"t": text, "c": class, "tip": hover text}], where class is
    ""        an ordinary word
    "wrong"   (base side) a span Parakh replaced
    "fix"     (Parakh side) a name written from context, with the reason as tip
    "num"     (Parakh side) a spoken number written as digits, with the words as tip
    "unsure"  a name-like word no other recogniser backs: shown as a question, not guessed
"""

from __future__ import annotations

from harness.numbers import find_numbers, fmt


def why(edit: dict, trace: dict, verified: set[str]) -> str:
    """One plain sentence on why a name was written."""
    name = edit.get("term", edit["to"])
    if edit.get("kind") == "consensus":
        return "no context needed: the other recognisers agree with each other on this word, so it outvotes the base"
    who = "a name you know" if name in verified else "a name heard in this call"
    exact = trace.get("wrote_exactly", {}).get(name, [])
    writers = trace.get("wrote_it", {}).get(name, [])
    if name in trace.get("corroborated", []) and exact:
        return f"{who}; {_short(exact[0])} wrote it unprompted and another recogniser heard something close"
    if name in trace.get("corroborated", []) and writers:
        return f"{who}; {_short(writers[0])} heard the same sound unprompted, spelt differently, and another recogniser heard something close"
    votes = trace.get("votes", {})
    if votes.get(name):
        others = ", ".join(f"{n} {v}" for n, v in votes.items() if n != name) or "no rival"
        return f"{who}; it won a three-way re-listen ({name} {votes[name]}, {others})"
    return f"{who}; a second listen with a short hint list chose it"


def _short(recogniser: str) -> str:
    return {"saaras-v4 translit": "Saaras v4", "saaras-v3 translit": "Saaras v3",
            "gpt-transcribe + hi/en": "gpt-transcribe", "yours": "your recogniser"}.get(recogniser, recogniser)


def _plain(words: list[str], digits: bool) -> list[dict]:
    """A run of untouched words, with clear number phrases marked."""
    if not digits or not words:
        return [{"t": w, "c": ""} for w in words]
    out, pos = [], 0
    for n in find_numbers(" ".join(words)):
        out += [{"t": w, "c": ""} for w in words[pos : n["start"]]]
        tail = words[n["end"] - 1][len(words[n["end"] - 1].rstrip(".,!?;:।")):]
        out.append({"t": fmt(n["value"]), "tail": tail, "c": "num", "tip": f"said: {n['text']}", "info": {"said": n["text"]}})
        pos = n["end"]
    return out + [{"t": w, "c": ""} for w in words[pos:]]


def view(base: str, trace: dict, verified: set[str] = frozenset(), digits: bool = True) -> dict:
    """{"base": [...], "parakh": [...]} for one segment."""
    toks = base.split()
    marks: dict[int, tuple[int, str, dict]] = {}  # start -> (end, kind, payload)
    for e in trace.get("edits", []):
        marks[e["span"][0]] = (e["span"][1], "fix", e)
    for u in [*trace.get("unsure_spans", []), *trace.get("number_doubts", [])]:
        if not any(a < u["span"][1] and u["span"][0] < b for a, (b, _, _) in marks.items()):
            marks[u["span"][0]] = (u["span"][1], "unsure", u)
    for c in trace.get("number_checks", []):  # a disputed number the speakers' own arithmetic settled
        if not any(a < c["span"][1] and c["span"][0] < b for a, (b, _, _) in marks.items()):
            marks[c["span"][0]] = (c["span"][1], "checked", c)

    base_view, parakh_view, run, i = [], [], [], 0
    while i < len(toks):
        if i not in marks:
            run.append(toks[i])
            base_view.append({"t": toks[i], "c": ""})
            i += 1
            continue
        end, kind, payload = marks[i]
        parakh_view += _plain(run, digits)
        run = []
        tail = toks[end - 1][len(toks[end - 1].rstrip(".,!?;:।")):]  # punctuation stays outside the highlight
        words = " ".join(toks[i:end])
        words = words[: len(words) - len(tail)] if tail else words
        if kind == "checked":
            wrote = {_short(trace.get("base", "")): payload["value"], **{_short(w): t for w, t in payload["heard"].items()}}
            info = {"said": words, "checked": payload["why"], "heard": wrote}
            base_view.append({"t": words, "tail": tail, "c": "", "info": info})
            parakh_view.append({"t": payload["value"], "tail": tail, "c": "num", "tip": f"{payload['why']}", "info": info})
        elif kind == "fix":
            reason = payload.get("why") if payload.get("kind") == "number" else why(payload, trace, verified)
            wrote = {_short(trace.get("base", "")): payload["from"], **{_short(w): t for w, t in payload.get("heard", {}).items()}}
            info = {"from": payload["from"], "to": payload["to"], "why": reason, "heard": wrote}
            base_view.append({"t": words, "tail": tail, "c": "wrong", "info": info})
            parakh_view.append({"t": payload["to"], "tail": tail, "c": "num" if payload.get("kind") == "number" else "fix",
                                "tip": f"heard as “{payload['from']}”; {reason}", "info": info})
        else:
            wrote = {_short(trace.get("base", "")): payload["text"], **{_short(w): t for w, t in payload["heard"].items()}}
            heard = "; ".join(f"{w}: “{t or 'nothing'}”" for w, t in wrote.items())
            tip = f"no other recogniser backs this. {heard}"
            number = payload.get("kind") == "number"
            info = {"text": payload["text"], "heard": wrote if number or not payload.get("options") else {},
                    "options": payload.get("options", []), "kind": payload.get("kind", "name"), "q": payload.get("q")}
            base_view.append({"t": words, "tail": tail, "c": "unsure", "tip": tip, "info": info})
            parakh_view.append({"t": payload["value"] if number else words, "tail": tail, "c": "unsure", "tip": tip, "info": info})
        i = end
    parakh_view += _plain(run, digits)
    return {"base": base_view, "parakh": parakh_view}
