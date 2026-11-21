from harness.parakh import number_doubts, number_fixes, products_said


def test_both_other_recognisers_agreeing_fixes_the_base():
    heard = {"a": "antim score 1 ank ki jeet", "b": "antim score 21 ank ki jeet", "c": "अंतिम स्कोर इक्कीस अंक की जीत"}
    (fix,) = number_fixes(heard, "a")
    assert (fix["from"], fix["to"], fix["kind"]) == ("1", "21", "number")
    assert number_doubts(heard, "a", [tuple(fix["span"])]) == []


def test_two_others_agreeing_in_different_scripts_fix_it_but_a_split_vote_only_asks():
    heard = {"a": "Ek sau saath nag", "b": "168 nag", "c": "एक सौ अड़सठ नग"}
    assert [f["to"] for f in number_fixes(heard, "a")] == ["168"]
    heard = {"a": "Ek sau saath nag", "b": "170 nag", "c": "एक सौ अड़सठ नग"}
    assert number_fixes(heard, "a") == [] and len(number_doubts(heard, "a")) == 1


def test_the_speakers_arithmetic_settles_a_disputed_number():
    heard = {"a": "Teen sau saath nag aa jayenge. Chaalis into chaar.", "b": "nag aa jayenge. Chaalis into chaar.", "c": "एक सौ साठ नग आ जाएँगे। चालीस इंटू चार।"}
    assert products_said(heard) == {160.0: "40 × 4"}
    (fix,) = number_fixes(heard, "a")
    assert fix["to"] == "160" and "40 × 4" in fix["why"]
    # and when the base already has the product, the doubt is dropped instead of asked
    heard = {"a": "Ek sau saath nag aa jayenge. Chaalis into chaar.", "b": "Ek sau saath nag.", "c": "तीन सौ साठ नग आ जाएँगे। चालीस इंटू चार।"}
    assert number_fixes(heard, "a") == [] and number_doubts(heard, "a") == []


def test_an_agreed_number_is_never_touched():
    heard = {"a": "Rate 5600 hai", "b": "Rate 5600 hai", "c": "रेट पाँच हजार छह सौ है"}
    assert number_fixes(heard, "a") == [] and number_doubts(heard, "a") == []
