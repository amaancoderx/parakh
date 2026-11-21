from harness.phonetic import key, same_sound, similarity, skeleton
from harness.score import false_insertions, score_clip, span_hit


def test_spelling_variants_share_a_key():
    assert key("Prathyusha") == key("Pratyusha")
    assert key("Sreenidhi") == key("Srinidhi")
    assert key("Sahoo") == key("Sahu")
    assert key("Reddy") == key("Reddi")
    assert key("Hi-Tech City") == key("Hi Tech City")


def test_devanagari_and_roman_are_the_same_sound():
    for dev, rom in [
        ("अखिलेश", "Akhilesh"), ("दामराजू", "Damaraju"), ("मेहरा", "Mehra"), ("डॉक्टर", "Doctor"),
        ("पेटीएम", "Paytm"), ("नायर", "Nair"), ("अपॉइंटमेंट", "appointment"), ("डिलीवर", "deliver"),
        ("कैंसल", "cancel"), ("मिनट", "minute"), ("गचीबौली", "Gachibowli"),
    ]:
        assert same_sound(dev, rom), (dev, rom, key(dev), key(rom))


def test_different_names_are_not_the_same_sound():
    for a, b in [("Mehta", "Mehra"), ("Kishan", "Keshav"), ("Nair", "Mair"), ("Irfan", "Imran"),
                 ("Akhil Damera", "Akhilesh Damaraju"), ("गमेराजू", "Damaraju")]:
        assert not same_sound(a, b), (a, b)
    assert skeleton("Mehta") != skeleton("Mehra")
    assert similarity("Damiraju", "Damaraju") > similarity("Damera", "Damaraju")


def test_devanagari_output_gets_credit_for_names():
    assert span_hit(["Doctor Mehra", "Dr Mehra"], "डॉक्टर मेहरा का अपॉइंटमेंट कैंसल कर दो।")
    assert span_hit(["Akhila Damaraju"], "अखिला दामराजू को पाँच सौ रुपये भेज दो।")
    assert not span_hit(["Akhilesh Damaraju"], "अखिलेश गमेराजू बाय फ्राइडे।")
    # Roman-script output must be exact: a misspelt name is a miss
    assert not span_hit(["Akhilesh Damaraju"], "to Akhilesh Damiraju by Friday")


def test_devanagari_loanwords_are_not_word_errors():
    ref = "Doctor Mehra ka appointment cancel kar do"
    r = score_clip(ref, "डॉक्टर मेहरा का अपॉइंटमेंट कैंसल कर दो।", [["Doctor Mehra"]], [])
    assert r["wer"] == 0 and r["entity_hits"] == [True]


def test_false_insertion_is_detected_in_both_scripts():
    ctx = ["Keshav Reddy", "Kiran Uppalapati"]
    assert false_insertions("Call Kishan Reddy", "Call Keshav Reddy and tell him", ctx) == ["Keshav Reddy"]
    assert false_insertions("Call Kishan Reddy", "केशव रेड्डी को कॉल करो", ctx) == ["Keshav Reddy"]
    assert false_insertions("Call Keshav Reddy", "Call Keshav Reddy", ctx) == []


def test_clean_devanagari_folds_variants_but_keeps_vowel_signs():
    from harness.phonetic import clean_devanagari
    assert clean_devanagari("मेरा नाम राहुल है") == "मेरा नाम राहुल है"
    assert clean_devanagari("आँख") == clean_devanagari("आंख")
    assert clean_devanagari("हिन्दी") == clean_devanagari("हिंदी")
    assert clean_devanagari("ज़रूरी") == clean_devanagari("जरूरी")
    assert clean_devanagari("क्‍या") == "क्या"
    assert clean_devanagari("१२३") == "123"
