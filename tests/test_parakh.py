"""The parts of the pipeline that need no API: finding mentions and writing names into a transcript."""

from harness.context import ContextIndex
from harness.parakh import disputed_positions, find_mentions, transplant

INDEX = ContextIndex({
    "contacts": ["Akhilesh Damaraju", "Akhil Damera", "Keshav Reddy", "Mohammad bhai"],
    "brands": ["Arizona Bianco", "Amazon Bianco", "Eicher"],
})


def term(name):
    return INDEX.by_text[name]


def test_mentions_find_a_garbled_name_and_ignore_everyday_words():
    found = find_mentions("Please transfer two lakh rupees to Akhilesh Damiraju by Friday.", INDEX)
    assert [m.text for m in found] == ["Akhilesh Damiraju"]
    assert found[0].candidates[0][0].text == "Akhilesh Damaraju"
    assert find_mentions("Kal subah jaldi uthna hai aur gym jaana hai.", INDEX) == []
    assert find_mentions("The meeting got postponed to next week.", INDEX) == []


def test_a_disputed_word_gets_a_lower_bar():
    text = "Ajina Bank ko. Kya? Thik hai."
    assert find_mentions(text, INDEX) == []
    found = find_mentions(text, INDEX, disputed=frozenset({0, 1}))
    assert found and found[0].candidates[0][0].text == "Arizona Bianco"


def test_transplant_writes_the_name_where_another_transcript_has_it():
    base = "Uska naam hai apna. Erojuna Baiyankho. Achha."
    other = "Uska naam hai apna Arizona Bianco. Achha."
    text, edits = transplant(base, [other], [term("Arizona Bianco")])
    assert text == "Uska naam hai apna. Arizona Bianco. Achha."
    assert [(e["from"], e["to"]) for e in edits] == [("Erojuna Baiyankho", "Arizona Bianco")]


def test_transplant_never_swallows_a_neighbouring_word():
    base = "Call Keshav Reddy and tell him the invoice is ready."
    text, edits = transplant(base, [base], [term("Keshav Reddy")], disputed=frozenset(range(10)))
    assert text == base and edits == []


def test_transplant_respells_a_same_sound_name_the_way_it_is_saved():
    text, edits = transplant("Send it to Akhilesh Damiraju today.", [], [term("Akhilesh Damaraju")])
    assert text == "Send it to Akhilesh Damaraju today."


def test_garbled_repeat_is_rewritten_only_where_no_other_recogniser_backs_the_word():
    base = "Ajina Bank ko. Kya? Ajina Bank ko, thik hai?"
    hinted = "Arizona Bianco. Kya? thik hai?"
    backed_nowhere = frozenset({0, 4})
    text, _ = transplant(base, [hinted], [term("Arizona Bianco")], disputed=backed_nowhere)
    assert text.count("Arizona Bianco") == 2
    text, _ = transplant(base, [hinted], [term("Arizona Bianco")], disputed=frozenset())
    assert text.count("Arizona Bianco") == 1  # the repeat stays as heard when another recogniser agrees with it


def test_disputed_positions():
    texts = {"a": "Kaun Mohan bhai haan", "b": "Kaun Mohan bhai haan", "c": "कौन मोहम्मद भाई हाँ"}
    some = disputed_positions(texts)
    alone = disputed_positions(texts, alone=True)
    assert some["a"] == frozenset({1})  # c heard that word differently
    assert alone["a"] == frozenset()  # but b backs it
    assert alone["c"] == frozenset({1})  # nobody backs c's version
