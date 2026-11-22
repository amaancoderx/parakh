"""The one-clip endpoint, with stand-in recognisers: no network."""
import time
import wave

from harness import service


def _clip(tmp_path):
    path = tmp_path / "clip.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\0\0" * 16000)
    return path


def _stand_ins(monkeypatch, delay=0.0):
    heard = {"saaras-v4 translit": "Teen ka kyon lo phir? Aishar mein lo to chaar ka hi lo",
             "saaras-v3 translit": "Teen ka kyon lo phir? Eicher mein lo toh chaar ka hi lo",
             "gpt-transcribe + hi/en": "तीन का क्यों लो फिर? आईशर में लो तो चार का ही लो"}

    def recogniser(name):
        def call(audio):
            if name != "saaras-v4 translit":
                time.sleep(delay)
            return {"text": heard[name], "latency_s": 0.01, "cached": False}
        return call

    monkeypatch.setattr(service, "_systems", {name: recogniser(name) for name in heard})


def test_draft_comes_first_then_the_checked_transcript(tmp_path, monkeypatch):
    _stand_ins(monkeypatch)
    steps = list(service._verify(_clip(tmp_path), ["Eicher"], "", "", 0, time.perf_counter()))
    assert [s["event"] for s in steps] == ["draft", "verified"]
    assert "Aishar" in steps[0]["transcript"]  # the base model's own words, untouched
    final = steps[1]
    assert "Eicher mein lo" in final["transcript"] and "Aishar" not in final["transcript"]
    assert final["parakh"]["edits"][0]["from"] == "Aishar" and final["parakh"]["edits"][0]["to"] == "Eicher"
    assert final["parakh"]["extra_listens"] == 0  # another recogniser wrote the name unprompted
    assert set(final) >= {"request_id", "transcript", "language_code", "timestamps", "diarized_transcript"}  # Sarvam's fields


def test_without_names_nothing_is_changed(tmp_path, monkeypatch):
    _stand_ins(monkeypatch)
    final = list(service._verify(_clip(tmp_path), [], "", "", 0, time.perf_counter()))[-1]
    assert final["transcript"] == final["parakh"]["base"]["transcript"] and final["parakh"]["edits"] == []


def test_your_own_transcript_becomes_the_base(tmp_path, monkeypatch):
    _stand_ins(monkeypatch)
    mine = "Teen ka kyon lo phir? Aishar mein lo to chaar ka hi lo"
    steps = list(service._verify(_clip(tmp_path), ["Eicher"], "", mine, 0, time.perf_counter()))
    assert steps[0]["transcript"] == mine and steps[0]["model"] == "your recogniser"
    assert steps[1]["parakh"]["recognisers"] == ["your recogniser", "Saaras v4", "gpt-transcribe"]  # one fewer call
    assert "Eicher mein lo" in steps[1]["transcript"]


def test_a_slow_recogniser_is_left_out_when_the_budget_runs_out(tmp_path, monkeypatch):
    _stand_ins(monkeypatch, delay=0.6)
    final = list(service._verify(_clip(tmp_path), ["Eicher"], "", "", 100, time.perf_counter()))[-1]
    assert final["parakh"]["recognisers"] == ["Saaras v4"] and len(final["parakh"]["left_out"]) == 2
    assert final["parakh"]["timing_ms"]["verified"] < 500


def test_a_word_is_timed_by_its_share_of_the_letters():
    text = "aaaa bbbb cccc dddd"
    assert service._when(text, 0, 10.0, 20.0) == 10.0
    assert service._when(text, 2, 10.0, 20.0) == 20.0  # half the letters come before the third word


def test_a_key_is_metered_and_refused_when_its_allowance_is_used(tmp_path, monkeypatch):
    from harness import account
    monkeypatch.setattr(account, "KEYS", tmp_path / "keys.json")
    monkeypatch.setattr(account, "LOG", tmp_path / "requests.jsonl")
    key = account.new_key("test")["key"]
    assert account.has_room(key, 60) and not account.has_room(key, account.FREE_SECONDS + 1)
    account.charge(key, 30, account.cost_inr(30))
    account.log("/speech-to-text", key[:10], 30, 1200, account.cost_inr(30), replayed=False)
    used = account.usage(key)
    assert used["minutes_used"] == 0.5 and used["requests"] == 1 and used["cost_to_run_inr"] > 0
    assert account.totals() == {"requests": 1, "audio_minutes": 0.5, "cost_to_run_inr": round(account.cost_inr(30), 2), "median_ms_per_clip": 1200}
    assert account.usage("pk_nope") is None


def test_a_finished_call_can_be_read_back_after_a_restart(tmp_path, monkeypatch):
    from harness import account
    monkeypatch.setattr(account, "CALLS", tmp_path / "calls")
    job = {"id": "abc123", "title": "Call", "seconds": 49.0, "questions": [{"id": 0, "answer": None}, {"id": 1, "answer": "160"}],
           "deal_sheet": {"summary": "About tiles."}, "topic": ""}
    account.save_call("dad", job, tmp_path / "call.wav")
    assert account.load_call("abc123")["job"]["title"] == "Call" and account.load_call("zzz") is None
    (listed,) = account.list_calls("dad")
    assert listed["open"] == 1 and listed["about"] == "About tiles."
    account.forget_calls("dad")
    assert account.list_calls("dad") == []


def test_the_answer_says_whether_anything_is_left_to_confirm(tmp_path, monkeypatch):
    _stand_ins(monkeypatch)
    final = list(service._verify(_clip(tmp_path), ["Eicher"], "", "", 0, time.perf_counter()))[-1]
    assert final["parakh"]["clear"] is True and final["parakh"]["confirm"] == []


def test_keys_are_named_listed_masked_and_revoked_by_their_owner_only(tmp_path, monkeypatch):
    from harness import account
    monkeypatch.setattr(account, "KEYS", tmp_path / "keys.json")
    made = account.new_key("Production", "u-a")
    listed = account.list_keys("u-a")
    assert [k["label"] for k in listed] == ["Production"] and made["key"] not in str(listed)
    assert account.list_keys("u-b") == []
    assert not account.revoke("u-b", made["id"])  # someone else's key
    assert account.revoke("u-a", made["id"]) and account.usage(made["key"]) is None


def test_speech_to_text_refuses_a_missing_or_unknown_key(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from harness import account
    monkeypatch.setattr(account, "KEYS", tmp_path / "keys.json")
    monkeypatch.delenv("PARAKH_ACCESS_CODE", raising=False)
    client = TestClient(service.app)
    clip = _clip(tmp_path).read_bytes()
    for headers in ({}, {"api-subscription-key": "pk_" + "0" * 32}):
        r = client.post("/speech-to-text", headers=headers, files={"file": ("clip.wav", clip, "audio/wav")})
        assert r.status_code == 401


def test_a_name_two_people_confirmed_is_shared_with_a_third_as_a_candidate(tmp_path, monkeypatch):
    from harness import memory
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.confirm("a", "Eicher")
    memory.confirm("b", "Eicher")
    memory.confirm("a", "Arizona Bianco")
    shared = memory.shared_names(exclude="c")
    assert list(shared) == ["Eicher"] and shared["Eicher"]["users"] == 2  # one person's word is not enough
    assert "Eicher" not in memory.shared_names(exclude="a") or memory.shared_names(exclude="a") == {}  # the second confirmer alone does not make it shared
