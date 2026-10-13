"""Théâtre de Beaulieu (beaulieu-lausanne.com/agenda/?cat=theatre).

Each show is a card with its date or short run ("28–29 octobre 2026",
"31 octobre – 1 novembre 2026"), title, image and page. No time, no price.
"""
from __future__ import annotations

from datetime import date
from typing import Callable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from sources.common import french_dates, text

NAME = "beaulieu"
HOSTS = ("beaulieu-lausanne.com",)


def read(html: str, page_url: str, fetch: Callable[[str], str], today: date) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    events = []
    for card in soup.select("article.excerpt-event"):
        days = french_dates(text(card.select_one("time")))
        title = text(card.select_one(".excerpt-title"))
        if not days or not title or days[-1] < today:
            continue
        link = card.select_one("a[href]")
        bg = card.select_one("[data-bg]")
        events.append({
            "title": title,
            "date": days[0].isoformat(),
            "end_date": days[-1].isoformat() if days[-1] != days[0] else "",
            "location": text(card.select_one(".excerpt-cat li")) or "Théâtre de Beaulieu",
            "image": bg["data-bg"] if bg else "",
            "url": urljoin(page_url, link["href"]) if link else page_url,
        })
    return events
