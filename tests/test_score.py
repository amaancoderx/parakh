from harness.data import load_manifest
from harness.score import aggregate, normalize, score_clip, span_hit


def test_normalize():
    assert normalize("Rs. 2,50,000 to Dr. Mehta!") == "rs 250000 to dr mehta"
    assert normalize("8.5% at 4:30 a.m.") == "8.5 at 4 30 a m"
    assert normalize("Mail sandeep.sahu@gmail.com.") == "mail sandeep.sahu@gmail.com"
    assert normalize("tomorrow's") == normalize("tomorrows")
    # Devanagari is romanised with the silent final vowel dropped, then spelling-folded
    assert normalize("अखिलेश को भेजो।") == "akhilesh ko bhejo"
    assert normalize("अखिलेश को ढाई लाख रुपये भेज दो") == normalize("Akhilesh ko dhai lakh rupaye bhej do")
    assert normalize("मैं पहुँच रहा हूँ") == normalize("main pahunch raha hoon")
    assert normalize("ढाई") == normalize("dhaai")


def test_script_mismatch_is_not_an_error():
    ref = "Akhilesh ko dhai lakh rupaye bhej do kal subah tak"
    r = score_clip(ref, "अखिलेश को ढाई लाख रुपये भेज दो कल सुबह तक।", [["Akhilesh"]], [["dhai lakh", "2.5 lakh"]])
    assert r["wer"] == 0 and r["entity_hits"] == [True] and r["format_hits"] == [True]
    assert r["non_latin_share"] == 1.0


def test_span_hit_variants_and_spacing():
    assert span_hit(["dhai lakh", "2.5 lakh", "250000"], "Send 2,50,000 rupees")
    assert span_hit(["9844077712"], "my number is 98440 77712")
    assert span_hit(["Hitech City", "Hitec City"], "reaching Hi-Tech City")
    assert not span_hit(["Akhilesh Damaraju"], "to Akilesh Damraju")


def test_score_clip_breakdown():
    ref = "Please transfer two and a half lakh rupees to Akhilesh Damaraju by Friday"
    ents = [["Akhilesh Damaraju"]]
    fmts = [["two and a half lakh", "2.5 lakh", "250000"]]

    perfect = score_clip(ref, ref + ".", ents, fmts)
    assert perfect["wer"] == 0 and perfect["entity_hits"] == [True]

    bad = score_clip(ref, "Please transfer 2.5 lakh rupees to Akilesh Damraju by Friday", ents, fmts)
    assert bad["entity_hits"] == [False]
    assert bad["format_hits"] == [True]  # digit rendering is credited
    assert bad["errors_by_cat"]["entity"] == 2
    assert bad["errors_by_cat"].get("other", 0) == 0

    agg = aggregate([perfect, bad])
    assert agg["entity_acc"] == 0.5 and agg["format_acc"] == 1.0
    assert agg["error_rate_by_cat"]["entity"] == 0.5


def test_empty_hypothesis():
    r = score_clip("call Keshav Reddy", "", [["Keshav Reddy"]], [])
    assert r["wer"] == 1.0 and r["entity_hits"] == [False]


def test_manifest_is_valid_and_split():
    clips = load_manifest()
    assert len(clips) == 54
    splits = {c.split for c in clips}
    assert splits == {"dev", "test"}
