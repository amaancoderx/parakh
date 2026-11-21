import json

from harness.compare import external_systems, markdown_table, score_system
from harness.data import load_manifest
from harness.score import normalize
from harness.systems import available_systems, context_terms


def test_table_ranks_better_system_first():
    clips = load_manifest(split="dev")[:3]
    good = {c.id: {"text": c.ref, "latency_s": 1.0} for c in clips}
    bad = {c.id: {"text": "hello there", "latency_s": 0.5} for c in clips}
    partial = {clips[0].id: {"text": clips[0].ref}}

    results = {
        "bad": score_system(clips, bad),
        "good": score_system(clips, good),
        "partial": score_system(clips, partial),
    }
    assert results["good"]["aggregate"]["entity_acc"] == 1.0
    assert results["bad"]["aggregate"]["entity_acc"] == 0.0

    rows = markdown_table(results, len(clips)).splitlines()[2:]
    assert rows[-1].startswith("| bad |")
    assert "1/3 (partial)" in next(r for r in rows if r.startswith("| partial |"))
    assert "n/a" in next(r for r in rows if r.startswith("| partial |"))  # no latency for file-based systems


def test_external_transcripts_are_loaded(tmp_path):
    (tmp_path / "some-app.jsonl").write_text(json.dumps({"id": "c01", "text": "hi"}) + "\n")
    assert external_systems(tmp_path) == {"some-app": {"c01": "hi"}}


def test_context_covers_every_clip_entity():
    terms = {normalize(t) for t in context_terms()}
    generic = {normalize(t) for t in ("upi", "ifsc", "aadhaar", "akhilesh", "doctor mehta", "doctor mehra", "chandrasekhar azad")}
    for clip in load_manifest():
        if "trap-oob" in clip.tags:  # deliberately absent from the context
            continue
        for variants in clip.entities:
            e = normalize(variants[0])
            assert e in terms or e in generic, f"{clip.id}: {variants[0]} missing from context.json"


def test_openai_systems_always_listed():
    assert {"gpt-4o-transcribe", "gpt-transcribe", "gpt-transcribe + keywords + hi/en"} <= set(available_systems())
