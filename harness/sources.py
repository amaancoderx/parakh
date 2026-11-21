"""Names from the files a user feeds into memory: contact lists, party ledgers, stock sheets.

    .vcf          a phone's contact export: the display name of each card
    .csv .xlsx    a sheet: the columns that hold names (Name, Party, Customer, Company, Item, Brand...);
                  without such a header, every column that is mostly words rather than numbers
    .txt          one name per line, or separated by commas

Only names are kept. Phone numbers, emails, amounts and dates are dropped, so a ledger can be
uploaded as it is.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

NAME_HEADERS = re.compile(
    r"name|contact|party|customer|client|supplier|vendor|company|firm|shop|business|brand|item|product|model|"
    r"transport|driver|city|place|area|naam|grahak", re.I)
SKIP_HEADERS = re.compile(r"phone|mobile|number|no\.?$|email|mail|amount|rate|price|qty|quantity|date|gst|pin|balance|total", re.I)
MAX_NAMES = 2000
CONTACT_KINDS = (".csv", ".xlsx", ".xlsm", ".vcf", ".txt", ".tsv")
AUDIO_KINDS = (".mp4", ".m4a", ".mp3", ".wav", ".ogg", ".opus", ".webm", ".aac", ".amr", ".3gp", ".mov")


def clean(raw: str) -> str | None:
    """A cell or line as a name, or None if it is not one."""
    name = re.sub(r"\s+", " ", str(raw or "")).strip(" \t\"'.,;:-")
    if not 3 <= len(name) <= 60:
        return None
    if not re.search(r"[^\W\d_]", name) or sum(c.isdigit() for c in name) > 3:  # a number, an amount, a date
        return None
    if "@" in name or re.search(r"\d{5,}", name) or re.fullmatch(r"[\d\s/:.-]+", name):
        return None  # an email, a phone number, a date
    return name


def _from_rows(rows: list[list[str]]) -> list[str]:
    rows = [[str(c or "").strip() for c in r] for r in rows if any(str(c or "").strip() for c in r)]
    if not rows:
        return []
    header, body = rows[0], rows[1:]
    picked = [i for i, h in enumerate(header) if NAME_HEADERS.search(h) and not SKIP_HEADERS.search(h)]
    if not picked:  # no header we know: keep columns that are mostly names, header row included
        body = rows
        width = max(len(r) for r in rows)
        picked = [i for i in range(width)
                  if sum(1 for r in rows if i < len(r) and clean(r[i])) >= max(1, 0.6 * sum(1 for r in rows if i < len(r) and r[i]))]
    out = []
    for r in body:
        for i in picked:
            if i < len(r) and (name := clean(r[i])):
                out.append(name)
    return out


def _vcf(text: str) -> list[str]:
    names = []
    for line in text.splitlines():
        if line.upper().startswith("FN") and ":" in line:
            names.append(line.split(":", 1)[1].replace("\\,", ",").strip())
    return [n for n in map(clean, names) if n]


def names_from_file(filename: str, data: bytes) -> list[str]:
    """Every name in a contacts or business file, in file order, without repeats."""
    kind = Path(filename).suffix.lower()
    if kind in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        found = [n for sheet in book.worksheets for n in _from_rows([list(r) for r in sheet.iter_rows(values_only=True)])]
    else:
        text = data.decode("utf-8-sig", errors="replace")
        if kind == ".vcf" or "BEGIN:VCARD" in text[:200].upper():
            found = _vcf(text)
        elif kind in (".csv", ".tsv"):
            dialect = "excel-tab" if kind == ".tsv" or text.count("\t") > text.count(",") else "excel"
            found = _from_rows(list(csv.reader(io.StringIO(text), dialect=dialect)))
        else:
            found = [n for n in map(clean, re.split(r"[\n,;]+", text)) if n]
    seen, out = set(), []
    for n in found:
        if n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out[:MAX_NAMES]
