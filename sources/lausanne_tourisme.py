"""Lausanne Tourisme (lausanne-tourisme.ch/fr/evenement/), the broadest agenda.

The listing page carries every event (over a thousand, bars and clubs
included) with its date or period, venue, title, image and a short text,
but no time and no price.

A period on the listing ("24.11.2025 - 30.11.2026") can be an exhibition
open every day or a karaoke held only on Mondays. Each event page tells
which: it lists its periods with the opening days and hours. So the event
pages of whatever happens in the next DETAIL_DAYS days are read too, for
the real dates, the start time, the price and the full text.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta
from typing import Callable
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from config import config

NAME = "lausanne-tourisme"
HOSTS = ("lausanne-tourisme.ch",)

TZ = ZoneInfo("Europe/Zurich")
DETAIL_DAYS = 7          # read the event pages of what happens this week
OCCURRENCE_DAYS = 14     # list the dates of a recurring event this far ahead
LONG_PERIOD_DAYS = 7     # a longer period without its event page is held back
EVERY_DAY = 5            # open at least this many days a week: one card, not one per day
CACHE_SECONDS = 12 * 3600

_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_cache: dict[str, tuple[float, dict]] = {}


def _day(text: str) -> list[date]:
    days = []
    for d, m, y in _DATE.findall(text or ""):
        try:
            days.append(date(int(y), int(m), int(d)))
        except ValueError:
            continue
    return days


def _text(tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split()) if tag else ""


def read_listing(html: str, page_url: str) -> list[dict]:
    """Every event of the listing page, with date objects for its period."""
    soup = BeautifulSoup(html, "lxml")
    events = []
    for teaser in soup.select(".teaser--post-type-event"):
        link = teaser.find("a", href=True)
        title = _text(teaser.select_one(".teaser__title"))
        days = _day(_text(teaser.select_one(".date__date")))
        if not link or not title or not days:
            continue
        img = teaser.select_one("img.teaser__image")
        events.append({
            "title": title,
            "start": days[0],
            "end": days[-1],
            "location": _text(teaser.select_one(".gmtLocation")),
            # The listing cuts the text mid-word ("dyn..."): show it as cut.
            "description": re.sub(r"\s*\.\.\.$", "…", _text(teaser.select_one(".teaser__content"))),
            "image": img.get("src", "") if img else "",
            "url": urljoin(page_url, link["href"]),
        })
    return events


def _clock(hhmm: str) -> str:
    return f"{hhmm[:2]}:{hhmm[2:]}" if re.fullmatch(r"\d{4}", hhmm or "") else ""


def _local_day(timestamp) -> date:
    return datetime.fromtimestamp(int(timestamp), TZ).date()


def _js_weekday(day: date) -> int:
    """Weekday numbered as on the site: 0 = Sunday ... 6 = Saturday."""
    return (day.weekday() + 1) % 7


def _start_times(openings: list[dict]) -> dict[int, str]:
    """Start time per weekday, leaving out the after-midnight end of a night.

    "Samedi 23:00-23:59, Dimanche 00:00-05:00" is one night starting on
    Saturday, not a second event on Sunday.
    """
    days = {o.get("day") for o in openings}
    starts: dict[int, str] = {}
    for o in openings:
        day = o.get("day")
        if o.get("from") == "0000" and (day - 1) % 7 in days:
            continue
        starts.setdefault(day, _clock(o.get("from", "")))
    return starts


def occurrences(start: date, end: date, openings: list[dict]) -> list[tuple[date, date | None, str]]:
    """(date, end date or None, start time) for one period of an event page."""
    starts = _start_times(openings)
    if start >= end:
        return [(start, None, starts.get(_js_weekday(start), ""))]
    if not starts or len(starts) >= EVERY_DAY:
        return [(start, end, "")]  # opening hours are not a start time
    found, day = [], start
    while day <= end:
        if _js_weekday(day) in starts:
            found.append((day, None, starts[_js_weekday(day)]))
        day += timedelta(days=1)
    return found


def read_detail(html: str) -> dict:
    """Periods, address, price and full text of an event page."""
    soup = BeautifulSoup(html, "lxml")
    box = soup.select_one("[x-show=\"tab === 'schedules_and_address'\"]") or soup
    periods = []
    for tag in box.select(".js-openingHours[data-opening]"):
        try:
            data = json.loads(tag["data-opening"])
            periods.append((_local_day(data["starts"]), _local_day(data["ends"]),
                            data.get("openings") or []))
        except (ValueError, KeyError, TypeError):
            continue

    address = ""
    block = box.select_one(".address")
    if block:
        lines = [s.strip() for s in block.find_all(string=True, recursive=False) if s.strip()]
        address = ", ".join(lines[1:])  # first line is the venue's name

    price = ""
    label = soup.find("h4", string=lambda s: s and "prix" in s.lower())
    if label and label.find_next_sibling("p"):
        price = _text(label.find_next_sibling("p"))
        if price and "gratuit" not in price.lower():
            price = f"Dès {price}"

    description = ""
    story = soup.select_one(".story__content")
    if story:
        for title in story.select(".story__title"):
            title.decompose()
        description = re.sub(r"\s*Source\s*:.*$", "", _text(story))

    return {"periods": periods, "address": address, "price": price, "description": description}


def _detail(url: str, fetch: Callable[[str], str], pause: float) -> dict | None:
    cached = _cache.get(url)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1]
    if pause:
        time.sleep(pause)  # one page at a time, gently
    try:
        detail = read_detail(fetch(url))
    except Exception:  # a missing page leaves the listing data as it is
        return None
    _cache[url] = (time.time(), detail)
    return detail


def _raw(item: dict, day: date, end: date | None = None, time_str: str = "", detail: dict | None = None) -> dict:
    detail = detail or {}
    return {
        "title": item["title"],
        "date": day.isoformat(),
        "end_date": end.isoformat() if end and end != day else "",
        "time": time_str,
        "location": item["location"],
        "address": detail.get("address", ""),
        "description": detail.get("description") or item["description"],
        "image": item["image"],
        "price": detail.get("price", ""),
        "url": item["url"],
    }


def _from_detail(item: dict, detail: dict, today: date) -> list[dict]:
    found = [occ for start, end, openings in detail["periods"]
             for occ in occurrences(start, end, openings)
             if (occ[1] or occ[0]) >= today]
    found.sort(key=lambda occ: occ[0])
    horizon = today + timedelta(days=OCCURRENCE_DAYS)
    near = [occ for occ in found if occ[0] <= horizon]
    return [_raw(item, day, end, t, detail) for day, end, t in (near or found[:1])]


def read(html: str, page_url: str, fetch: Callable[[str], str], today: date,
         max_pages: int | None = None, pause: float | None = None) -> list[dict]:
    max_pages = config.MAX_DETAIL_PAGES if max_pages is None else max_pages
    pause = config.SCRAPE_PAUSE_SECONDS if pause is None else pause
    window_end = today + timedelta(days=DETAIL_DAYS)

    listing = [item for item in read_listing(html, page_url) if item["end"] >= today]
    this_week = sorted((item for item in listing if item["start"] <= window_end),
                       key=lambda item: max(item["start"], today))
    to_read = {item["url"] for item in this_week[:max_pages]}

    events = []
    for item in listing:
        detail = _detail(item["url"], fetch, pause) if item["url"] in to_read else None
        if detail and detail["periods"]:
            events.extend(_from_detail(item, detail, today))
        elif item["start"] == item["end"]:
            events.append(_raw(item, item["start"]))
        elif (item["end"] - item["start"]).days <= LONG_PERIOD_DAYS or item["start"] > window_end:
            # A short run, or a period that starts later (read once it comes near).
            events.append(_raw(item, item["start"], item["end"]))
        # else: a long period under way whose days are unknown is held back,
        # rather than shown every evening.
    return events
