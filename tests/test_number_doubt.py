from harness.numbers import numbers_in, to_digits
from harness.parakh import number_doubts


def test_digits_before_a_multiplier_are_one_number():
    assert to_digits("5 hazaar rupaye") == "5,000 rupaye"
    assert to_digits("2.5 lakh ka maal") == "2,50,000 ka maal"
    assert to_digits("5 hazaar 6 sau") == "5,600"
    assert to_digits("rate 5. Hazaar log aaye") == "rate 5. 1,000 log aaye"  # a sentence break keeps them apart


def test_numbers_are_found_however_they_are_written():
    assert [n["value"] for n in numbers_in("160 nag ya ek sau adsath nag")] == [160, 168]
    assert [n["value"] for n in numbers_in("पाँच हजार छह सौ के हिसाब")] == [5600]


def test_the_same_number_in_three_forms_is_not_doubted():
    heard = {"a": "Rate paanch hazaar chhe sau hai", "b": "Rate 5600 hai", "c": "रेट पाँच हजार छह सौ है"}
    assert number_doubts(heard, "a") == []


def test_a_number_nobody_else_heard_is_asked_about():
    heard = {"a": "Usne ek sau saath nag bheje the kal", "b": "Usne 168 nag bheje the kal", "c": "उसने एक सौ अड़सठ नग भेजे थे कल"}
    (doubt,) = number_doubts(heard, "a")
    assert doubt["value"] == "160" and doubt["options"] == ["160", "168"] and doubt["span"] == (1, 4)


def test_one_recogniser_agreeing_is_enough():
    heard = {"a": "Usne ek sau saath nag bheje", "b": "Usne 160 nag bheje", "c": "उसने एक सौ अड़सठ नग भेजे"}
    assert number_doubts(heard, "a") == []
