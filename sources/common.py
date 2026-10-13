"""Small helpers shared by the source readers."""
from __future__ import annotations

import re
from datetime import date

from agenda import fold

MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
}
# "16", "1er", "28 octobre", "29 octobre 2026"
_PART = re.compile(r"\b(\d{1,2})(?:er)?(?:\s+(" + "|".join(MONTHS) + r"))?(?:\s+(\d{4}))?\b")


def text(tag) -> str:
    """Visible text of a tag on one line ("" when the tag is missing)."""
    return " ".join(tag.get_text(" ", strip=True).split()) if tag else ""


def french_dates(value: str) -> list[date]:
    """Dates written in French, in order: "jeudi 15 octobre 2026",
    "28–29 octobre 2026", "31 octobre – 1 novembre 2026".

    A day without month or year takes those written after it, as French
    does; a month later than the next one belongs to the year before
    ("30 décembre – 2 janvier 2027").
    """
    parts = _PART.findall(fold(value))
    found: list[date] = []
    month = year = None
    for day, month_name, year_text in reversed(parts):
        next_month = month
        month = MONTHS.get(month_name, month)
        if year_text:
            year = int(year_text)
        elif month_name and next_month and MONTHS[month_name] > next_month and year:
            year -= 1
        if month is None or year is None:
            continue
        try:
            found.append(date(year, month, int(day)))
        except ValueError:
            continue
    return sorted(found)
