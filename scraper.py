"""Scraper for Lausanne cultural sources.

Strategy, for each configured source URL:
    1. iCalendar feed (BEGIN:VCALENDAR): read its VEVENT entries.
    2. Sites with their own reader (SITE_READERS): read the page with the
       rules written for that site.
    3. JSON-LD structured data (schema.org/Event variants) on the page.
    4. Listing pages of known aggregators (config.DETAIL_LINK_PATTERNS):
       follow the links to each event page and read its JSON-LD.
A page in none of these formats gives no event: guessing events from the
page layout produced menus and headings without dates. SOURCES.md lists
which sources use which format, and those still waiting for a reader.

Every source run is logged with the method used and the number of events
found, so /api/sources can show which sources actually work.

The scraper is intentionally defensive: any individual page failure is
logged and skipped, never raised.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from agenda import fold, today_local
from config import config
import db

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Europe/Zurich")

EVENT_TYPES = {
    "Event", "MusicEvent", "TheaterEvent", "DanceEvent",
    "VisualArtsEvent", "Festival", "ExhibitionEvent",
    "ScreeningEvent", "ComedyEvent",
}

CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    # Order matters — first match wins. Clubbing before Musique to catch DJ/techno.
    # Keywords match whole words only, with or without accents, singular or
    # plural ("concert" also finds "Concerts"; "rap" does not find "photographie").
    "Clubbing":  ("techno", "house", "club night", "afterparty", "after-party",
                  "after party", "rave", "warehouse", "underground", "boiler room",
                  "dj set", "afterhour", "all night", "d! club", "mad club",
                  "folklore", "datcha"),
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
    "Danse":     ("danse", "ballet", "chorégraphie", "flamenco", "performance"),
    "Festival":  ("festival", "fête", "nuit des musées", "open air"),
    "Famille":   ("famille", "enfant", "jeune public", "marionnette"),
    "Conférence": ("conférence", "débat", "symposium", "lecture", "talk"),
    "Sport":     ("sport", "marathon", "course", "match", "tournoi"),
    "Humour":    ("humour", "comedy", "stand-up", "one-man-show"),
    "Atelier":   ("atelier", "workshop", "initiation"),
    "Marché":    ("marché", "foire", "artisanat"),
}

# Expressions that contain a keyword but mean something else.
IGNORED_EXPRESSIONS: tuple[str, ...] = ("pop-up",)

# Venues whose programme is of one kind decide the theme before any keyword:
# a film at the Cinémathèque stays a film even when its summary says
# "famille" or "rock". Venues with a mixed programme are left out.
VENUE_RULES: dict[str, tuple[str, ...]] = {
    "Clubbing":  ("d! club", "mad", "folklor", "base bar", "barberousse"),
    "Cinéma":    ("cinémathèque", "cinéma", "zinéma", "pathé"),
    "Musique":   ("les docks", "le romandie", "jumeaux jazz club", "chorus",
                  "satellite", "bcv concert hall", "hemu", "opéra de lausanne"),
    "Théâtre":   ("vidy", "arsenic", "kléber-méleau", "théâtre 2.21", "pulloff",
                  "petit théâtre", "café théâtre"),
    "Exposition": ("musée", "photo elysée", "mudac", "mcba", "plateforme 10"),
}


def _keyword_pattern(keywords: Iterable[str]) -> re.Pattern:
    """Whole words or phrases, accent-free, with an optional plural s or x."""
    words = "|".join(re.escape(fold(kw)) for kw in keywords)
    return re.compile(rf"(?<!\w)(?:{words})[sx]?(?!\w)")


_CATEGORY_PATTERNS = [(cat, _keyword_pattern(kws)) for cat, kws in CATEGORY_RULES.items()]
_VENUE_PATTERNS = [(cat, _keyword_pattern(kws)) for cat, kws in VENUE_RULES.items()]
_IGNORED_PATTERN = _keyword_pattern(IGNORED_EXPRESSIONS)


def _gen_id(title: str, date: str) -> str:
    return hashlib.md5(f"{title}|{date}".encode("utf-8")).hexdigest()[:10]


def categorize(title: str, description: str = "", venue: str = "") -> str:
    place = " ".join(fold(venue).split())
    for category, pattern in _VENUE_PATTERNS:
        if pattern.search(place):
            return category
    text = " ".join(fold(f"{title} {description}").split())
    text = _IGNORED_PATTERN.sub(" ", text)
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    return "Culture"


def _parse_iso_date(value: str) -> tuple[str, str]:
    if not value:
        return "", ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value[:10], ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(LOCAL_TZ)
    # A bare date ("2026-10-16") carries no time: do not show "00:00".
    has_time = "T" in value or " " in value.strip()
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M") if has_time else ""


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
                address.get("addressLocality", ""),
            ]
            address = ", ".join(p for p in parts if p)
        return name, address
    if isinstance(location_field, str):
        return location_field, ""
    return "", ""


def _extract_price(offers) -> str:
    """Price text from schema.org offers, or "" when the source gives none."""
    if isinstance(offers, list):
        texts = [t for t in (_extract_price(o) for o in offers) if t]
        return " / ".join(dict.fromkeys(texts))
    if not isinstance(offers, dict):
        return ""
    low, high = offers.get("lowPrice"), offers.get("highPrice")
    price = offers.get("price", low)
    currency = offers.get("priceCurrency") or "CHF"
    try:
        if price is not None and float(str(price).replace(",", ".")) == 0:
            return "Gratuit"
    except ValueError:
        return str(price).strip()
    if low is not None and high is not None and str(low) != str(high):
        return f"{currency} {low}–{high}"
    return f"{currency} {price}" if price not in (None, "") else ""


def _normalize_jsonld(item: dict, page_url: str = "") -> dict | None:
    title = (item.get("name") or "").strip()
    if not title:
        return None

    date, time_str = _parse_iso_date(item.get("startDate", ""))
    end_date, _ = _parse_iso_date(item.get("endDate", ""))
    location_field = item.get("location")
    if isinstance(location_field, list):
        location_field = location_field[0] if location_field else None
    location, address = _extract_location(location_field)
    description = BeautifulSoup(item.get("description") or "", "lxml").get_text(" ", strip=True)[:400]
    price = _extract_price(item.get("offers"))
    if not price and item.get("isAccessibleForFree") in (True, "true", "True"):
        price = "Gratuit"

    return {
        "id": _gen_id(title, date),
        "title": title,
        "date": date,
        "time": time_str,
        "end_date": end_date,
        "location": location,
        "address": address,
        "category": categorize(title, description, location),
        "subcategory": "",
        "description": description,
        "image": _extract_image(item.get("image")),
        "price": price,
        "url": item.get("url") or page_url,
        "tags": [],
        "featured": False,
    }


def _jsonld_items(data) -> Iterable[dict]:
    """Walk JSON-LD: plain objects, lists and @graph containers."""
    if isinstance(data, list):
        for entry in data:
            yield from _jsonld_items(entry)
    elif isinstance(data, dict):
        if "@graph" in data:
            yield from _jsonld_items(data["@graph"])
        yield data


def _is_event(item: dict) -> bool:
    kind = item.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    return any(k in EVENT_TYPES for k in kinds)


def _extract_jsonld_events(soup: BeautifulSoup, page_url: str = "") -> list[dict]:
    events: list[dict] = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for item in _jsonld_items(data):
            if not _is_event(item):
                continue
            normalized = _normalize_jsonld(item, page_url)
            if normalized:
                events.append(normalized)
    return events


def _unfold_ics(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _ics_value(value: str) -> str:
    return (value.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",")
            .replace("\\;", ";").replace("\\\\", "\\").strip())


def _ics_date(key: str, value: str) -> tuple[str, str]:
    """DTSTART / DTEND: date-only, local, or UTC (Z) values."""
    value = value.strip()
    if "VALUE=DATE" in key and len(value) == 8:
        return f"{value[:4]}-{value[4:6]}-{value[6:]}", ""
    m = re.match(r"(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})\d{0,2}(Z?))?$", value)
    if not m:
        return "", ""
    y, mo, d, hh, mm, utc = m.groups()
    if hh is None:
        return f"{y}-{mo}-{d}", ""
    iso = f"{y}-{mo}-{d}T{hh}:{mm}:00" + ("+00:00" if utc else "")
    return _parse_iso_date(iso)


def parse_ics(text: str, page_url: str = "") -> list[dict]:
    """Read VEVENT entries from an iCalendar feed."""
    events: list[dict] = []
    current: dict[str, str] | None = None
    for line in _unfold_ics(text):
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            title = _ics_value(current.get("SUMMARY", ""))
            date, time_str = current.get("_start", ("", ""))
            end_date, _ = current.get("_end", ("", ""))
            if title:
                description = _ics_value(current.get("DESCRIPTION", ""))[:400]
                location = _ics_value(current.get("LOCATION", ""))
                venue, _, address = location.partition(",")
                events.append({
                    "id": _gen_id(title, date), "title": title, "date": date,
                    "time": time_str, "end_date": end_date if end_date != date else "",
                    "location": venue.strip(), "address": address.strip(),
                    "category": categorize(title, description, venue), "subcategory": "",
                    "description": description, "image": "", "price": "",
                    "url": current.get("URL", "").strip() or page_url,
                    "tags": [], "featured": False,
                })
            current = None
        elif current is not None and ":" in line:
            key, _, value = line.partition(":")
            name = key.split(";")[0].upper()
            if name == "DTSTART":
                current["_start"] = _ics_date(key, value)
            elif name == "DTEND":
                current["_end"] = _ics_date(key, value)
            else:
                current[name] = value
    return events


def _detail_links(soup: BeautifulSoup, page_url: str, pattern: str) -> list[str]:
    """Event-page links on an aggregator listing page, in page order."""
    rule = re.compile(pattern)
    host = urlparse(page_url).netloc
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        url = urljoin(page_url, a["href"]).split("#")[0]
        if urlparse(url).netloc == host and rule.search(urlparse(url).path) and url not in links:
            links.append(url)
    return links


def _on_site(url: str, domain: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host == domain or host.endswith("." + domain)


def _detail_pattern(url: str) -> str | None:
    for domain, pattern in config.DETAIL_LINK_PATTERNS:
        if _on_site(url, domain):
            return pattern
    return None


def _text(tag) -> str:
    return tag.get_text(" ", strip=True) if tag else ""


_SWISS_DAY = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")


def read_lausanne_tourisme(text: str, page_url: str) -> list[dict]:
    """Event cards of www.lausanne-tourisme.ch/fr/evenement/ (all on one page).

    A card gives title, teaser, date ("01.11.2026") or range ("27.05.2026 -
    16.12.2026"), venue, image and link. Time and price are only on each
    event's own page and are not read here.
    """
    soup = BeautifulSoup(text, "lxml")
    events: list[dict] = []
    for card in soup.select("div.teaser--post-type-event"):
        title = _text(card.select_one(".teaser__title"))
        if not title:
            continue
        days = [f"{y}-{m}-{d}" for d, m, y in
                _SWISS_DAY.findall(_text(card.select_one(".teaser__suptitle .date__date")))]
        date = days[0] if days else ""
        end_date = days[-1] if days and days[-1] != date else ""
        description = _text(card.select_one(".teaser__content"))
        venue = _text(card.select_one(".gmtLocation"))
        link = card.select_one("a[href]")
        image = card.select_one("img.teaser__image")
        events.append({
            "id": _gen_id(title, date), "title": title, "date": date, "time": "",
            "end_date": end_date, "location": venue,
            "address": "", "category": categorize(title, description, venue), "subcategory": "",
            "description": description, "image": image.get("src", "") if image else "",
            "price": "", "url": urljoin(page_url, link["href"]) if link else page_url,
            "tags": [], "featured": False,
        })
    return events


# Sites read with their own rules: domain -> reader(page text, page URL).
SITE_READERS = {
    "lausanne-tourisme.ch": read_lausanne_tourisme,
}


def _site_reader(url: str):
    for domain, reader in SITE_READERS.items():
        if _on_site(url, domain):
            return domain, reader
    return None


class FetchError(Exception):
    pass


def _fetch(url: str) -> str:
    headers = {
        "User-Agent": config.SCRAPE_USER_AGENT,
        "Accept-Language": "fr-CH,fr;q=0.9,en;q=0.5",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=config.SCRAPE_TIMEOUT_SECONDS)
        resp.raise_for_status()
        # Without a declared charset, requests reads text as Latin-1, which
        # turns the UTF-8 "fête" of a calendar file into "fÃªte".
        if "charset" not in resp.headers.get("Content-Type", "").lower():
            resp.encoding = "utf-8"
        return resp.text
    except requests.RequestException as exc:
        raise FetchError(str(exc)) from exc


def scrape_one(url: str) -> tuple[list[dict], str, bool]:
    """Collect one source. Returns (events, method used, complete).

    complete is False when part of the source could not be read (an event
    page failed, or more event pages than MAX_DETAIL_PAGES): the events
    found are then not the source's whole programme. Raises FetchError.
    """
    text = _fetch(url)
    if text.lstrip().startswith("BEGIN:VCALENDAR"):
        return parse_ics(text, url), "ical", True

    site = _site_reader(url)
    if site:
        domain, reader = site
        return reader(text, url), f"lecteur {domain}", True

    soup = BeautifulSoup(text, "lxml")
    found = _extract_jsonld_events(soup, url)
    if found:
        return found, "json-ld", True

    pattern = _detail_pattern(url)
    if pattern:
        all_links = _detail_links(soup, url, pattern)
        links = all_links[: config.MAX_DETAIL_PAGES]
        failed = 0
        for link in links:
            try:
                page = BeautifulSoup(_fetch(link), "lxml")
            except FetchError as exc:
                logger.warning("Detail page failed %s: %s", link, exc)
                failed += 1
                continue
            found.extend(_extract_jsonld_events(page, link))
        complete = failed == 0 and len(links) == len(all_links)
        return found, f"pages-detail ({len(links)} liens)", complete

    return [], "aucun format reconnu", True


# Venue names that two sources write differently for the same place.
VENUE_ALIASES: dict[str, str] = {
    "salle paderewski": "casino de montbenon",  # the hall inside the Casino
}

# Title words too common to show that two titles name the same event.
_GENERIC_WORDS = {
    "les", "des", "une", "the", "and", "avec", "pour", "sur", "dans", "par", "aux",
    "concert", "soiree", "spectacle", "visite", "guidee", "atelier", "exposition",
    "film", "projection", "festival", "live", "party", "night", "show",
}


def _venue_key(venue: str) -> str:
    key = " ".join(fold(venue).split())
    return VENUE_ALIASES.get(key, key)


def _title_words(title: str) -> set[str]:
    words = {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"\w+", fold(title))}
    return {w for w in words if len(w) >= 3 and w not in _GENERIC_WORDS}


def _drop_duplicates(events: list[dict]) -> list[dict]:
    """Remove an event that a later source gives again under another title.

    Two events are the same when they start the same day at the same venue
    and their titles share a distinctive word ("OCL: Grand Concert 2" and
    "Les Grands Concerts n°2 | Christie"). The later source's version is
    kept: venues come after aggregators and usually give the time.
    """
    kept: dict[str, dict] = {}
    by_slot: dict[tuple[str, str], list[str]] = {}
    for evt in events:
        slot = (evt.get("date", ""), _venue_key(evt.get("location", "")))
        if all(slot):
            words = _title_words(evt["title"])
            for other_id in by_slot.get(slot, []):
                other = kept.get(other_id)
                if other and other["source"] != evt["source"] and words & _title_words(other["title"]):
                    del kept[other_id]
            by_slot.setdefault(slot, []).append(evt["id"])
        kept[evt["id"]] = evt
    return list(kept.values())


def scrape_sources(sources: Iterable[str] | None = None) -> tuple[list[dict], dict[str, int]]:
    """Scrape every source URL.

    Returns the deduplicated events, each tagged with the source URL that
    gave it (the last one when several sources give the same event, see
    _drop_duplicates), and the number of events given by each source that
    answered in full.
    """
    sources = sources or config.SCRAPE_SOURCES
    aggregated: dict[str, dict] = {}
    complete_counts: dict[str, int] = {}

    for url in sources:
        try:
            found, method, complete = scrape_one(url)
        except FetchError as exc:
            logger.warning("Fetch failed for %s: %s", url, exc)
            db.log_scrape("scraper", url, "error", 0, str(exc)[:300])
            continue

        for evt in found:
            evt["source"] = url
            aggregated[evt["id"]] = evt
        if found and complete:
            complete_counts[url] = len(found)

        status = "ok" if found else "empty"
        db.log_scrape("scraper", url, status, len(found), method)
        logger.info("Scraped %d events from %s (%s)", len(found), url, method)

    return _drop_duplicates(list(aggregated.values())), complete_counts


def refresh_database(sources: Iterable[str] | None = None) -> int:
    """Run a scrape pass and persist results. Returns number of events written.

    Each source's list is the reference for the events stored under it: an
    event it no longer announces (cancelled, removed) is deleted, unless
    another source still announces it. Nothing is deleted for a source that
    failed, came back empty or incomplete, or suddenly gives fewer than half
    of its upcoming events: that looks more like a broken page than a
    programme that emptied.
    """
    events, complete_counts = scrape_sources(sources)
    if events:
        db.bulk_upsert(events)
        logger.info("Persisted %d scraped events", len(events))

    announced = {evt["id"] for evt in events}
    today = today_local().isoformat()
    for url, count in complete_counts.items():
        if count * 2 < db.count_upcoming(url, today):
            logger.warning("Kept the events of %s: it now gives only %d", url, count)
            continue
        removed = db.delete_unannounced(url, announced)
        if removed:
            logger.info("Removed %d events no longer announced by %s", removed, url)
    return len(events)
