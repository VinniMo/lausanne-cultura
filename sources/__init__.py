"""Source-specific readers, for sites the generic collection cannot read.

Each reader module exposes:
    NAME   short label written to the collection log
    HOSTS  the domains it handles
    read(html, page_url, fetch, today) -> list of raw events

A raw event carries what the source says (title, date as YYYY-MM-DD, and
when known time, end_date, location, address, description, image, price,
url). The collector adds the identifier and the theme.
"""
from __future__ import annotations

from types import ModuleType
from urllib.parse import urlparse

from sources import lausanne_tourisme

READERS: tuple[ModuleType, ...] = (lausanne_tourisme,)


def reader_for(url: str) -> ModuleType | None:
    host = urlparse(url).netloc.lower()
    for reader in READERS:
        if any(host == h or host.endswith("." + h) for h in reader.HOSTS):
            return reader
    return None
