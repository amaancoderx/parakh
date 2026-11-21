from harness.phonetic import key, key_distance, key_length, key_similarity, similarity_at_least

WORDS = ["Eicher", "Aishar", "Arizona Bianco", "Ajina Bank", "Mohammad bhai", "Mohan bhai", "Keshav Reddy", "Kishan Reddy",
         "न्यूट गिंग्रिच", "न्यूट ग्रीनरिज", "पिट्सबर्ग", "पीटर्सबर्ग", "अमेरिका", "अफ्रीका", "yaar", "Akhilesh Damaraju", "एपीएस"]


def test_the_shortcut_gives_the_same_answer_as_the_full_distance():
    keys = [key(w) for w in WORDS]
    for a in keys:
        for b in keys:
            for floor in (0.58, 0.68, 0.7, 0.8):
                full, fast = key_similarity(a, b), similarity_at_least(a, b, floor)
                assert fast == full if full >= floor else fast < floor, (a, b, floor, full, fast)


def test_the_distance_is_never_less_than_the_difference_in_length():
    keys = [key(w) for w in WORDS]
    for a in keys:
        for b in keys:
            assert key_distance(a, b) >= abs(key_length(a) - key_length(b)) - 1e-9
