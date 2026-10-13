"""D! Club (dclub.ch/agenda/): the club's own programme, its ABC bar included.

Each night is a card carrying its date (data-date="20261016"), the room,
the party name, the line-up, the door time and the flyer. No price.
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Callable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sources.common import text

NAME = "dclub"
HOSTS = ("dclub.ch",)
ROOMS = {"d-club": "D! Club", "abc": "Bar Club ABC"}


def read(html: str, page_url: str, fetch: Callable[[str], str], today: date) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    events = []
    for card in soup.select(".event[data-date]"):
        found = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", card["data-date"].strip())
        if not found:
            continue
        day = date(*map(int, found.groups()))
        if day < today:
            continue
        party = text(card.select_one(".dtitle"))
        lineup = " / ".join(t for t in (text(n) for n in card.select(".artist .name")) if t)
        title = party or lineup
        if not title:
            continue
        if party and lineup:
            title = f"{party} · {lineup}"
        door = re.search(r"(\d{1,2})[:h](\d{2})", text(card.select_one(".door")))
        try:
            room = (json.loads(card.get("data-place") or "[]") or [""])[0]
        except ValueError:
            room = ""
        img = card.select_one("a.image img")
        image = (img.get("data-lazy-src") or img.get("src") or "") if img else ""
        link = card.select_one("a.main[href]") or card.select_one("a[href]")
        details = [text(card.select_one(s)) for s in (".style", ".age")]
        events.append({
            "title": title,
            "date": day.isoformat(),
            "time": f"{int(door.group(1)):02d}:{door.group(2)}" if door else "",
            "location": ROOMS.get(room, "D! Club"),
            "description": " · ".join(d for d in details if d),
            "image": "" if image.startswith("data:") else image,
            # One page per date; the anchor (#d-club, #abc) points to the room.
            "url": urljoin(page_url, link["href"]) if link else page_url,
            "key": f"dclub|{day}|{room}|{title}",
        })
    return events
