import pytest

from harness.numbers import find_numbers, fmt, to_digits


@pytest.mark.parametrize("spoken, value", [
    ("chhe hazaar chhe sau", 6600),
    ("paanch hazaar chhe sau", 5600),
    ("Paanch hazaar chhah sau", 5600),
    ("ek sau adsath", 168),
    ("ek sau saath", 160),
    ("teen sau saath", 360),
    ("aath sau battis", 832),
    ("saat sau feet", 700),
    ("dhai lakh", 250000),
    ("dedh sau", 150),
    ("saadhe teen sau", 350),
    ("paune do lakh", 175000),
    ("ek crore bees lakh", 12000000),
    ("एक सौ अड़सठ", 168),
    ("पाँच हज़ार छह सौ", 5600),
    ("ढाई लाख", 250000),
    ("चालीस", 40),
    ("bayalis set", 42),
    ("baawan feet", 52),
    ("two and a half lakh", 250000),
    ("two lakh", 200000),
    ("forty two thousand five hundred", 42500),
    ("one crore twenty lakh", 12000000),
    ("fifteen hundred", 1500),
])
def test_values(spoken, value):
    found = find_numbers(spoken)
    assert found, spoken
    assert found[0]["value"] == value, (spoken, found)


def test_real_call_sentences():
    assert to_digits("Paanch hazaar chhe sau nahi hai chhah hazaar chhe sau hogi.") == "5,600 nahi hai 6,600 hogi."
    assert to_digits("Ek sau saath nag aa jayenge.") == "160 nag aa jayenge."
    assert "168" in to_digits("aath aur maan ek sau adsath aa jayenge.")
    assert to_digits("chaalis set ya bayalis set kareeb") == "40 set ya 42 set kareeb"
    assert to_digits("Pickup mein baais aa jaate hain.") == "Pickup mein baais aa jaate hain."  # lone word, no unit: left alone


def test_ordinary_words_are_left_alone():
    for text in [
        "Please do so at once", "mere saath chalo", "kya haal chaal hain", "main do din mein aata hoon so jao",
        "theek hai na", "ek minute", "is car ko dekho", "to phir main karoon book",
        "Jod wala de denge aapko", "do dedh sau ke to ho gaye mere grahak",
    ]:
        assert to_digits(text) == text, (text, find_numbers(text))


def test_indian_grouping():
    assert fmt(168) == "168" and fmt(5600) == "5,600" and fmt(250000) == "2,50,000" and fmt(12000000) == "1,20,00,000"
    assert fmt(7.5) == "7.5"


def test_two_numbers_in_a_row_stay_two():
    assert to_digits("Aath sau aath sau, do by chaar hai.") == "800 800, do by chaar hai."
