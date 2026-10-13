"""Scraper for Lausanne cultural sources.

Strategy, for each configured source URL:
    1. A source-specific reader (sources/) when the site has one.
    2. iCalendar feed (BEGIN:VCALENDAR): read its VEVENT entries.
    3. JSON-LD structured data (schema.org/Event variants) on the page.
    4. Listing pages of known aggregators (config.DETAIL_LINK_PATTERNS):
       follow the links to each event page and read its JSON-LD.
    5. Fall back to HTML heuristics.

Only events with a readable date are kept.

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
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from agenda import fold, parse_day, today_local
from config import config
from sources import reader_for
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


# Venues that say what the event is better than its words: a film at the
# Cinémathèque whose summary mentions "famille" is still a film.
VENUE_FIRST: tuple[tuple[str, str], ...] = (
    (r"cinematheque|cinema|zinema", "Cinéma"),
    (r"\bmad\b|d! club|folklor|bar club abc", "Clubbing"),
)
# Venues used when the words give nothing: a museum may also host a talk.
VENUE_FALLBACK: tuple[tuple[str, str], ...] = (
    (r"\bdocks\b|romandie|jumeaux jazz|chorus|concert hall", "Musique"),
    (r"musee|mudac|mcba|elysee|plateforme 10|palais de rumine", "Exposition"),
    (r"theatre|pulloff", "Théâtre"),
    (r"\bbar\b|barberousse|captain cook|basebar", "Clubbing"),
)


# Whole words, plural allowed: "rap" must not match "Rappaz", nor
# "techno" match "technique".
_KEYWORDS = {kw: re.compile(rf"(?<!\w){re.escape(kw)}(?:s|x|e|es)?(?![\w-])")
             for kws in CATEGORY_RULES.values() for kw in kws}


def _venue_category(venue: str, rules: tuple[tuple[str, str], ...]) -> str | None:
    folded = fold(venue)
    return next((cat for pattern, cat in rules if re.search(pattern, folded)), None)


def categorize(title: str, description: str = "", venue: str = "") -> str:
    first = _venue_category(venue, VENUE_FIRST)
    if first:
        return first
    text = f"{title} {description}".lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(_KEYWORDS[kw].search(text) for kw in keywords):
            return category
    return _venue_category(venue, VENUE_FALLBACK) or "Culture"


def complete_event(raw: dict) -> dict:
    """Full event record from what a source-specific reader found."""
    evt = {key: raw.get(key, "") for key in (
        "title", "date", "time", "end_date", "location", "address",
        "description", "image", "price", "url")}
    # The event's own page identifies it best; the date tells repeats apart.
    evt["id"] = _gen_id(raw.get("key") or evt["url"] or evt["title"], evt["date"])
    evt["category"] = categorize(evt["title"], evt["description"], evt["location"])
    evt.update(subcategory="", tags=[], featured=False)
    return evt


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
        "category": categorize(title, description),
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
                    "category": categorize(title, description), "subcategory": "",
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


def _detail_pattern(url: str) -> str | None:
    host = urlparse(url).netloc.lower()
    for domain, pattern in config.DETAIL_LINK_PATTERNS:
        if host == domain or host.endswith("." + domain):
            return pattern
    return None


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
        if image:
            image = urljoin(base_url, image)

    link_tag = card.find("a", href=True)
    url = urljoin(base_url, link_tag["href"]) if link_tag else ""

    return {
        "id": _gen_id(title, date),
        "title": title,
        "date": date,
        "time": "",
        "end_date": "",
        "location": "",
        "address": "",
        "category": categorize(title, description),
        "subcategory": "",
        "description": description,
        "image": image,
        "price": "",
        "url": url,
        "tags": [],
        "featured": False,
    }


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
        return resp.text
    except requests.RequestException as exc:
        raise FetchError(str(exc)) from exc


def scrape_one(url: str) -> tuple[list[dict], str]:
    """Collect one source. Returns (events, method used). Raises FetchError."""
    text = _fetch(url)
    reader = reader_for(url)
    if reader:
        raw = reader.read(text, url, _fetch, today_local())
        return [complete_event(r) for r in raw], reader.NAME

    if text.lstrip().startswith("BEGIN:VCALENDAR"):
        return parse_ics(text, url), "ical"

    soup = BeautifulSoup(text, "lxml")
    found = _extract_jsonld_events(soup, url)
    if found:
        return found, "json-ld"

    pattern = _detail_pattern(url)
    if pattern:
        links = _detail_links(soup, url, pattern)[: config.MAX_DETAIL_PAGES]
        for link in links:
            try:
                page = BeautifulSoup(_fetch(link), "lxml")
            except FetchError as exc:
                logger.warning("Detail page failed %s: %s", link, exc)
                continue
            found.extend(_extract_jsonld_events(page, link))
        return found, f"pages-detail ({len(links)} liens)"

    return _extract_html_events(soup, base_url=url), "html"


# ----- The same event seen by several sources -----

# Words that do not tell two events apart. Lausanne Tourisme numbers its
# repeats ("Insomnia - 2"); the number is dropped too.
_TITLE_STOP = {"le", "la", "les", "de", "du", "des", "d", "l", "et", "en", "au", "aux",
               "a", "un", "une", "the", "of", "and", "x", "feat", "ft", "avec", "par",
               "pour", "sur", "by", "complet", "dj", "djs", "live"}
_VENUE_STOP = {"club", "bar", "theatre", "salle", "lausanne", "le", "la", "les", "de",
               "du", "des", "d", "l", "the", "et", "musee", "cantonal"}
SHORT_RUN_DAYS = 7


def _words(value: str, stop: set[str]) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", fold(value)) if w not in stop}


def _venue_words(evt: dict) -> set[str]:
    words = re.findall(r"[a-z0-9]+", fold(evt.get("location", "")))
    # "D! Club" is only common words: keep them rather than lose the venue.
    return {w for w in words if w not in _VENUE_STOP} or set(words)


def _title_words(evt: dict) -> set[str]:
    words = _words(re.sub(r"\s+-\s+\d+$", "", evt.get("title", "")), _TITLE_STOP)
    return {w for w in words if len(w) > 1}


def _is_long(evt: dict) -> bool:
    start = parse_day(evt["date"])
    end = parse_day(evt.get("end_date", "")) or start
    return (end - start).days > SHORT_RUN_DAYS


def _days(evt: dict) -> list[date]:
    """Days an event can be matched on: every day of a short run, else its start."""
    start = parse_day(evt["date"])
    end = parse_day(evt.get("end_date", "")) or start
    if end < start or _is_long(evt):
        return [start]
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def same_event(a: dict, b: dict) -> bool:
    """Same day (checked by the caller), close titles, same venue and time.

    When in doubt, two records stay apart: a duplicate is a lesser harm
    than an event that disappears.
    """
    if a.get("time") and b.get("time") and a["time"] != b["time"]:
        return False  # two showings
    if _is_long(a) != _is_long(b):
        return False  # an exhibition and its opening night
    ta, tb = _title_words(a), _title_words(b)
    if not ta or not tb:
        return False
    small, big = sorted((ta, tb), key=len)
    overlap = len(ta & tb) / len(ta | tb)
    va, vb = _venue_words(a), _venue_words(b)
    if va and vb:
        # "Les Docks" and "Salle de concert des Docks" are one venue;
        # "MAD – Mainfloor" and "MAD – Jetlag" are two floors.
        if not (va <= vb or vb <= va):
            return False
        return small <= big or overlap >= 0.7
    # A venue is unknown: the titles alone must say it.
    return (small <= big and len(small) >= 2) or overlap >= 0.8


_FILLABLE = ("time", "price", "address", "image", "description", "location")


def merge_duplicates(ranked: list[tuple[int, dict]]) -> list[dict]:
    """One record per event. ranked holds (source rank, event): the venue's
    own site outranks a general agenda. The kept record is completed with
    what the other one knows (time, price, address...)."""
    def richness(evt: dict) -> int:
        return sum(1 for field in _FILLABLE if evt.get(field))

    order = sorted(ranked, key=lambda pair: (-pair[0], -richness(pair[1])))
    kept: list[dict] = []
    by_day: dict[date, list[dict]] = {}
    for _, evt in order:
        twin = next((k for day in _days(evt) for k in by_day.get(day, ())
                     if k["id"] == evt["id"] or same_event(k, evt)), None)
        if twin is not None:
            for field in _FILLABLE:
                if not twin.get(field) and evt.get(field):
                    twin[field] = evt[field]
            continue
        kept.append(evt)
        for day in _days(evt):
            by_day.setdefault(day, []).append(evt)
    return kept


def scrape_sources(sources: Iterable[str] | None = None) -> list[dict]:
    """Scrape every source URL and return one record per event."""
    sources = sources or config.SCRAPE_SOURCES
    ranked: list[tuple[int, dict]] = []

    for url in sources:
        try:
            found, method = scrape_one(url)
        except FetchError as exc:
            logger.warning("Fetch failed for %s: %s", url, exc)
            db.log_scrape("scraper", url, "error", 0, str(exc)[:300])
            continue

        dated = [evt for evt in found if parse_day(evt.get("date", ""))]
        rank = 2 if url in config.SCRAPE_VENUES else 1
        ranked.extend((rank, evt) for evt in dated)

        # A card without a date does not help anyone choose an evening out.
        if len(dated) < len(found):
            method += f" · {len(found) - len(dated)} sans date écartés"
        status = "ok" if dated else "empty"
        db.log_scrape("scraper", url, status, len(dated), method)
        logger.info("Scraped %d dated events from %s (%s)", len(dated), url, method)

    events = merge_duplicates(ranked)
    logger.info("%d events after merging %d duplicates", len(events), len(ranked) - len(events))
    return events


def refresh_database() -> int:
    """Run a scrape pass and persist results. Returns number of events written."""
    events = scrape_sources()
    if events:
        db.bulk_upsert(events, source="scraper")
        logger.info("Persisted %d scraped events", len(events))
    return len(events)
