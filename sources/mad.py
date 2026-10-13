"""MAD (mad.ch/agenda/): the club's own programme, floor by floor.

Each night is a block of headings: the date ("jeudi 15 octobre 2026"),
the party name, the line-up and the floor ("JETLAG (3ème étage)"), with a
flyer and a ticketing link. No door time, no price ("Entrée libre" is
sometimes written in the line-up).
"""
from __future__ import annotations

from datetime import date
from typing import Callable

from bs4 import BeautifulSoup

from agenda import fold
from sources.common import french_dates, text

NAME = "mad"
HOSTS = ("mad.ch", "mad.club")


def _floor(value: str) -> str:
    """'JETLAG (3ÈME ÉTAGE)' -> 'Jetlag', 'mainfloor (REz)' -> 'Mainfloor'."""
    return value.split("(")[0].strip().capitalize()


def read(html: str, page_url: str, fetch: Callable[[str], str], today: date) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    events = []
    for heading in soup.find_all("h3"):
        days = french_dates(text(heading))
        if not days or days[0] < today:
            continue
        block = heading.find_parent(class_="e-con")
        if block is None:
            continue
        lines = [text(h) for h in block.find_all("h3")]
        rest = lines[lines.index(text(heading)) + 1:]
        if not rest:
            continue
        title, lineup, floor = (rest + ["", ""])[:3]
        outer = block.find_parent(class_="e-parent") or block
        img = outer.find("img")
        ticket = block.find("a", href=True)
        events.append({
            "title": title,
            "date": days[0].isoformat(),
            "location": f"MAD – {_floor(floor)}" if floor else "MAD",
            "description": " · ".join(p for p in (lineup, floor) if p),
            "price": "Entrée libre" if "entree libre" in fold(lineup) else "",
            "image": img.get("src", "") if img else "",
            "url": ticket["href"] if ticket else page_url,
            # Several nights share the agenda page: name and floor tell them apart.
            "key": f"mad|{title}|{floor}",
        })
    return events
