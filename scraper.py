"""Scraper for Lausanne cultural sources.

Strategy:
    1. GET each configured source URL.
    2. Parse JSON-LD structured-data blocks (schema.org/Event variants).
    3. Fall back to HTML heuristics if no structured data is present.

The scraper is intentionally defensive: any individual page failure is
logged and skipped, never raised.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Iterable

import requests
from bs4 import BeautifulSoup, Tag

from config import config
import apify_scraper
import db

logger = logging.getLogger(__name__)

EVENT_TYPES = {
    "Event", "MusicEvent", "TheaterEvent", "DanceEvent",
    "VisualArtsEvent", "Festival", "ExhibitionEvent",
    "ScreeningEvent", "ComedyEvent",
}

CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    # Order matters — first match wins. Clubbing before Musique to catch DJ/techno.
    "Clubbing":  ("techno", "house", "club night", "after", "rave", "warehouse",
                  "underground", "boiler room", "dj set", "afterhour", "all night",
                  "d! club", "mad club", "folklore", "datcha"),
    "Musique":   ("concert", "jazz", "rock", "classique", "opéra", "orchestre",
                  "récital", "électronique", "electro", "dj", "chanson", "vivaldi",
                  "beethoven", "brahms", "verdi", "live band", "punk", "metal",
                  "indie", "pop", "folk", "hip-hop", "rap"),
    "Théâtre":   ("théâtre", "pièce", "comédie", "tragédie", "hamlet",
                  "molière", "mise en scène", "spectacle", "monologue"),
    "Exposition": ("exposition", "expo", "vernissage", "galerie",
                   "rétrospective", "musée", "installation"),
    "Cinéma":    ("cinéma", "film", "projection", "documentaire",
                  "court-métrage", "ciné", "avant-première"),
    "Danse":     ("danse", "ballet", "chorégraphie", "flamenco",
                  "contemporain", "performance"),
    "Festival":  ("festival", "fête", "nuit des musées", "open air"),
    "Famille":   ("famille", "enfants", "jeune public", "marionnettes"),
    "Conférence": ("conférence", "débat", "symposium", "lecture", "talk"),
    "Sport":     ("sport", "marathon", "course", "match", "tournoi"),
    "Humour":    ("humour", "comedy", "stand-up", "one-man-show"),
    "Atelier":   ("atelier", "workshop", "initiation"),
    "Marché":    ("marché", "foire", "artisanat"),
}


def _gen_id(title: str, date: str) -> str:
    return hashlib.md5(f"{title}|{date}".encode("utf-8")).hexdigest()[:10]


def categorize(title: str, description: str = "") -> str:
    text = f"{title} {description}".lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(kw in text for kw in keywords):
            return category
    return "Culture"


def _parse_iso_date(value: str) -> tuple[str, str]:
    if not value:
        return "", ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except ValueError:
        return value[:10], ""


def _extract_image(image_field) -> str:
    if isinstance(image_field, list) and image_field:
        first = image_field[0]
        return first if isinstance(first, str) else first.get("url", "")
    if isinstance(image_field, dict):
        return image_field.get("url", "")
    if isinstance(image_field, str):
        return image_field
    return ""


def _extract_location(location_field) -> tuple[str, str]:
    if isinstance(location_field, dict):
        name = location_field.get("name", "")
        address = location_field.get("address", "")
        if isinstance(address, dict):
            parts = [
                address.get("streetAddress", ""),
                address.get("postalCode", ""),
                address.get("addressLocality", "Lausanne"),
            ]
            address = ", ".join(p for p in parts if p)
        return name, address or "Lausanne"
    if isinstance(location_field, str):
        return location_field, "Lausanne"
    return "Lausanne", "Lausanne"


def _normalize_jsonld(item: dict) -> dict | None:
    title = (item.get("name") or "").strip()
    if not title:
        return None

    date, time_str = _parse_iso_date(item.get("startDate", ""))
    end_date, _ = _parse_iso_date(item.get("endDate", ""))
    location, address = _extract_location(item.get("location"))
    description = (item.get("description") or "").strip()[:400]

    return {
        "id": _gen_id(title, date),
        "title": title,
        "date": date,
        "time": time_str,
        "end_date": end_date,
        "location": location,
        "address": address,
        "category": categorize(title, description),
        "subcategory": "",
        "description": description,
        "image": _extract_image(item.get("image")),
        "price": "Voir détails",
        "url": item.get("url", "#"),
        "tags": [],
        "featured": False,
    }


def _extract_jsonld_events(soup: BeautifulSoup) -> list[dict]:
    events: list[dict] = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") not in EVENT_TYPES:
                continue
            normalized = _normalize_jsonld(item)
            if normalized:
                events.append(normalized)
    return events


def _extract_html_events(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Heuristic fallback: scan for elements that look like event cards."""
    selector = re.compile(r"event|agenda|card|show|spectacle|concert", re.IGNORECASE)
    candidates = soup.find_all(["article", "li", "div"], class_=selector, limit=80)

    events: list[dict] = []
    for card in candidates:
        evt = _parse_card(card, base_url)
        if evt:
            events.append(evt)
    return events


def _parse_card(card: Tag, base_url: str) -> dict | None:
    title_tag = card.find(["h1", "h2", "h3", "h4"])
    if not title_tag:
        return None
    title = title_tag.get_text(strip=True)
    if not title or len(title) < 4:
        return None

    time_tag = card.find("time")
    date = ""
    if time_tag:
        date = (time_tag.get("datetime") or time_tag.get_text(strip=True))[:10]

    desc_tag = card.find("p")
    description = desc_tag.get_text(strip=True)[:400] if desc_tag else ""

    img_tag = card.find("img")
    image = ""
    if img_tag:
        image = img_tag.get("src", "") or img_tag.get("data-src", "")
        if image.startswith("/"):
            image = base_url.rstrip("/") + image

    link_tag = card.find("a", href=True)
    url = link_tag["href"] if link_tag else "#"
    if url.startswith("/"):
        url = base_url.rstrip("/") + url

    return {
        "id": _gen_id(title, date),
        "title": title,
        "date": date,
        "time": "",
        "end_date": "",
        "location": "Lausanne",
        "address": "Lausanne",
        "category": categorize(title, description),
        "subcategory": "",
        "description": description,
        "image": image,
        "price": "Voir détails",
        "url": url,
        "tags": [],
        "featured": False,
    }


def _fetch(url: str) -> str | None:
    headers = {
        "User-Agent": config.SCRAPE_USER_AGENT,
        "Accept-Language": "fr-CH,fr;q=0.9,en;q=0.5",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=config.SCRAPE_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.warning("Fetch failed for %s: %s", url, exc)
        db.log_scrape("scraper", url, "error", 0, str(exc))
        return None


def _extract_from_html(html: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    found = _extract_jsonld_events(soup)
    if not found:
        found = _extract_html_events(soup, base_url=url)
    return found


def scrape_sources(sources: Iterable[str] | None = None) -> list[dict]:
    """Scrape every source URL and return a deduplicated list of events.

    Standard ``requests`` pass first; for sources that yielded zero events
    (typically JS-heavy SPAs), retry through Apify when configured.
    """
    sources = sources or config.SCRAPE_SOURCES
    aggregated: dict[str, dict] = {}
    empty_sources: list[str] = []

    for url in sources:
        html = _fetch(url)
        if not html:
            empty_sources.append(url)
            continue

        found = _extract_from_html(html, url)
        for evt in found:
            aggregated[evt["id"]] = evt

        db.log_scrape("scraper", url, "ok", len(found))
        logger.info("Scraped %d events from %s", len(found), url)
        if not found:
            empty_sources.append(url)

    if empty_sources and apify_scraper.is_enabled():
        logger.info("Retrying %d empty sources via Apify", len(empty_sources))
        rendered = apify_scraper.fetch_many(empty_sources)
        for url, html in rendered.items():
            found = _extract_from_html(html, url)
            for evt in found:
                aggregated[evt["id"]] = evt
            db.log_scrape("apify", url, "ok", len(found))
            logger.info("Apify scraped %d events from %s", len(found), url)

    return list(aggregated.values())


def refresh_database() -> int:
    """Run a scrape pass and persist results. Returns number of events written."""
    events = scrape_sources()
    if events:
        db.bulk_upsert(events, source="scraper")
        logger.info("Persisted %d scraped events", len(events))
    return len(events)
