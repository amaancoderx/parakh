"""Feeding memory: files to names, the on/off switch, learning on its own, and isolation between keys."""
import io

from harness import memory, sources


def test_a_ledger_gives_names_and_drops_numbers_amounts_and_dates():
    csv = b"Party Name,Mobile,Balance,Date,Transport\nMohammad bhai,9876543210,12000,12/03/2026,Eicher\nJawar sahab,9811111111,500,01/04/2026,Tata 407\n"
    assert sources.names_from_file("ledger.csv", csv) == ["Mohammad bhai", "Eicher", "Jawar sahab", "Tata 407"]


def test_an_excel_sheet_a_phone_export_and_a_plain_list_are_all_read():
    from openpyxl import Workbook
    book = Workbook()
    for row in (("Customer", "Phone"), ("Gupta Traders", "9876500003"), ("Sharma Tiles", "9876500004")):
        book.active.append(row)
    buf = io.BytesIO()
    book.save(buf)
    assert sources.names_from_file("parties.xlsx", buf.getvalue()) == ["Gupta Traders", "Sharma Tiles"]
    vcf = b"BEGIN:VCARD\nFN:Ramesh Gupta\nTEL:9876500005\nEND:VCARD\nBEGIN:VCARD\nFN:Babu Bhai\nEND:VCARD\n"
    assert sources.names_from_file("contacts.vcf", vcf) == ["Ramesh Gupta", "Babu Bhai"]
    assert sources.names_from_file("names.txt", "Kajaria, Somany\nArizona Bianco\nkajaria".encode()) == ["Kajaria", "Somany", "Arizona Bianco"]


def test_a_name_is_trusted_on_its_own_only_after_separate_recordings(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    for call in ("c1", "c1", "c2"):  # the same call checked twice is one hearing
        memory.propose("u", {"Arizona Bianco": {"from": "a call", "call": call}})
    assert memory.auto_trust("u") == [] and memory.load("u")["candidates"]["Arizona Bianco"]["seen"] == 2
    memory.propose("u", {"Arizona Bianco": {"from": "a voice note", "call": "c3"}})
    assert memory.auto_trust("u") == ["Arizona Bianco"]
    entry = memory.load("u")["verified"]["Arizona Bianco"]
    assert entry["auto"] and "3 separate recordings" in entry["verified"]


def test_memory_off_is_remembered_and_a_file_can_be_taken_back(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.confirm_many("u", ["Eicher", "Mohammad bhai"], how="from ledger.csv", source="s1")
    memory.confirm("u", "Jawar sahab")
    memory.heard_as("u", {"Eicher": "Aishar"})
    assert memory.load("u")["verified"]["Eicher"]["heard_as"] == ["Aishar"]
    assert memory.enabled("u")
    memory.settings("u", enabled=False)
    assert not memory.enabled("u") and memory.verified("u")  # off keeps what it knows, it just is not used
    assert memory.drop_source("u", "s1") == 2 and memory.verified("u") == ["Jawar sahab"]


def test_each_api_key_and_each_of_its_users_get_their_own_memory(tmp_path, monkeypatch):
    from harness import account, service
    monkeypatch.setattr(account, "KEYS", tmp_path / "keys.json")
    a = account.new_key("A", "u-alpha")["key"]
    b = account.new_key("B", "u-beta")["key"]
    assert service._memory_user(a) == "u-alpha" and service._memory_user(b) == "u-beta"
    assert service._memory_user(a, "Amit") == "u-alpha--amit" != service._memory_user(b, "Amit")
