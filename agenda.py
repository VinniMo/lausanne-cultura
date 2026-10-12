"""Programme logic: what is still on, when, under which heading, at what price.

Pure functions only (no Flask, no SQLite) so the rules can be read and tested
in isolation. Every date comparison happens in Swiss local time.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Zurich")

# Display headings ("rubriques"), in screen order, and the scraper themes
# each one gathers. Anything not listed falls into "Autres".
RUBRICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Concerts", ("Musique",)),
    ("Soirées & clubs", ("Clubbing",)),
    ("Scène", ("Théâtre", "Danse", "Humour")),
    ("Cinéma", ("Cinéma",)),
    ("Expos", ("Exposition",)),
)
OTHER_RUBRIC = "Autres"
RUBRIC_ORDER: tuple[str, ...] = tuple(name for name, _ in RUBRICS) + (OTHER_RUBRIC,)
_RUBRIC_BY_CATEGORY = {cat.lower(): name for name, cats in RUBRICS for cat in cats}

SMALL_PRICE_CHF = 15

MOMENTS: tuple[tuple[str, str], ...] = (
    ("tonight", "Ce soir"),
    ("tomorrow", "Demain"),
    ("weekend", "Week-end"),
    ("later", "Plus tard"),
)

_FREE_WORDS = ("gratuit", "entree libre", "free", "prix libre", "chapeau")
_UNKNOWN_PRICES = ("", "voir details", "n. c.", "nc")
# An amount is a number written next to a currency mark ("CHF 18", "25.-",
# "20 fr."), or the upper end of a range ("CHF 35–85"). Other numbers
# ("3 jours", "dès 16 ans") are not prices.
_AMOUNT = re.compile(
    r"(?:chf|fr\.?|frs)\s*(\d+(?:[.,]\d+)?)(?:\s*[-–]\s*(\d+(?:[.,]\d+)?))?"
    r"|(\d+(?:[.,]\d+)?)\s*(?:chf|fr\b|frs|\.-|\.–)"
)
_BARE_AMOUNT = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*$")


def today_local(now: datetime | None = None) -> date:
    """Today's date in Lausanne, whatever the server's own timezone."""
    now = now or datetime.now(TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    return now.astimezone(TZ).date()


def fold(text: str) -> str:
    """Lowercase and strip accents so that 'opera' matches 'Opéra'."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def rubric_for(category: str) -> str:
    return _RUBRIC_BY_CATEGORY.get((category or "").strip().lower(), OTHER_RUBRIC)


def parse_day(value: str) -> date | None:
    try:
        return date.fromisoformat((value or "").strip()[:10])
    except ValueError:
        return None


def read_price(raw: str) -> dict:
    """Interpret a free-text price without ever guessing.

    Returns is_free, price_min (lowest CHF amount written, or None) and
    known (False when the source gave nothing usable).
    """
    text = fold(raw).strip()
    if text in _UNKNOWN_PRICES:
        return {"is_free": False, "price_min": None, "known": False}
    if any(word in text for word in _FREE_WORDS):
        return {"is_free": True, "price_min": 0, "known": True}
    found = [n for groups in _AMOUNT.findall(text) for n in groups if n]
    bare = _BARE_AMOUNT.match(text)
    if bare:
        found.append(bare.group(1))
    amounts = [float(n.replace(",", ".")) for n in found]
    if not amounts:
        return {"is_free": False, "price_min": None, "known": False}
    low = min(amounts)
    return {"is_free": low == 0, "price_min": int(low) if low.is_integer() else low, "known": True}


def is_small_price(evt: dict) -> bool:
    if evt.get("is_free"):
        return True
    low = evt.get("price_min")
    return low is not None and low <= SMALL_PRICE_CHF


def matches(evt: dict, query: str) -> bool:
    """Accent- and case-insensitive search over title, venue, text and tags."""
    needle = fold(query).strip()
    if not needle:
        return True
    haystack = fold(" ".join([
        evt.get("title", ""), evt.get("location", ""), evt.get("description", ""),
        evt.get("subcategory", ""), evt.get("category", ""), " ".join(evt.get("tags") or []),
    ]))
    return all(word in haystack for word in needle.split())


def weekend_days(today: date) -> tuple[date, date]:
    """The coming Saturday and Sunday (the current ones during a week-end)."""
    if today.weekday() == 6:  # Sunday: only today is left
        return today, today
    saturday = today + timedelta(days=(5 - today.weekday()) % 7)
    return saturday, saturday + timedelta(days=1)


def _time_key(evt: dict) -> tuple:
    t = (evt.get("time") or "").strip()
    return (t == "", t, fold(evt.get("title", "")))


def build_programme(events: list[dict], today: date) -> dict:
    """Drop past events and lay the rest out by moment, then by day.

    An event is past when its end date (or its start date when it has no end)
    is before today. A multi-day event appears on each of its days inside the
    Ce soir / Demain / Week-end windows; "Plus tard" lists, by start date,
    what starts after tomorrow outside the week-end, so long exhibitions
    already running are not repeated there.
    Events without a readable date are kept in "Plus tard", flagged undated.
    """
    tomorrow = today + timedelta(days=1)
    sat, sun = weekend_days(today)
    weekend = {sat, sun}

    upcoming: list[dict] = []
    undated: list[dict] = []
    for raw in events:
        evt = dict(raw)
        evt["rubric"] = rubric_for(evt.get("category", ""))
        evt.update(read_price(evt.get("price", "")))
        start = parse_day(evt.get("date", ""))
        end = parse_day(evt.get("end_date", "")) or start
        if start is None:
            evt["undated"] = True
            undated.append(evt)
            continue
        if end < start:
            end = start
        if end < today:
            continue
        evt["undated"] = False
        evt["_start"], evt["_end"] = start, end
        upcoming.append(evt)

    def on(day: date) -> list[str]:
        hits = [e for e in upcoming if e["_start"] <= day <= e["_end"]]
        return [e["id"] for e in sorted(hits, key=_time_key)]

    def window(*days: date) -> list[dict]:
        seen: list[date] = []
        for d in days:
            if d not in seen:
                seen.append(d)
        return [{"date": d.isoformat(), "ids": on(d)} for d in seen if on(d)]

    later_by_day: dict[date, list[dict]] = {}
    for e in upcoming:
        if e["_start"] > tomorrow and e["_start"] not in weekend:
            later_by_day.setdefault(e["_start"], []).append(e)
    later = [
        {"date": d.isoformat(), "ids": [e["id"] for e in sorted(later_by_day[d], key=_time_key)]}
        for d in sorted(later_by_day)
    ]
    if undated:
        later.append({"date": None, "ids": [e["id"] for e in sorted(undated, key=_time_key)]})

    days = {
        "tonight": window(today),
        "tomorrow": window(tomorrow),
        "weekend": window(sat, sun),
        "later": later,
    }
    moments = []
    for key, label in MOMENTS:
        ids = {i for block in days[key] for i in block["ids"]}
        moments.append({"key": key, "label": label, "count": len(ids), "days": days[key]})

    for e in upcoming:
        e["ongoing"] = e["_start"] < today
        e.pop("_start"), e.pop("_end")
    return {
        "today": today.isoformat(),
        "weekend": [sat.isoformat(), sun.isoformat()],
        "moments": moments,
        "events": upcoming + undated,
    }
