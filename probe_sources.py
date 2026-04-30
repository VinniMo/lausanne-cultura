"""Probe each priority source to validate which URLs work and what parser
strategy each one needs. Run this in Codespaces (unrestricted internet).

Usage:
    python probe_sources.py

For each candidate URL it reports:
    - HTTP status (200 = OK, 403 = blocked, 404 = wrong URL, ERR = DNS/timeout)
    - Body size in bytes
    - Number of schema.org Event entries found in JSON-LD
    - Whether a __NEXT_DATA__ blob is present (Next.js SPA, parseable as JSON)
    - Number of <article> elements (rough HTML-fallback proxy)

Use the output to decide, per venue, which URL to keep in config.py and which
parser strategy to apply (JSON-LD / __NEXT_DATA__ / per-site HTML / API).
"""
from __future__ import annotations

import json
import sys

import requests
from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-CH,fr;q=0.9,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Multiple URL candidates per venue: probe will tell us which one returns
# something usable. Order = best guess first.
CANDIDATES: list[tuple[str, list[str]]] = [
    ("Lausanne agenda", [
        "https://www.lausanne.ch/agenda-et-actualites/agenda.html",
    ]),
    ("Plateforme 10", [
        "https://plateforme10.ch/agenda",
        "https://plateforme10.ch/",
    ]),
    ("Folklore", [
        "https://www.lefolklore.ch/",
        "https://lefolklore.ch/",
        "https://folkloreclub.ch/",
        "https://folklore-club.ch/",
    ]),
    ("Romandie", [
        "https://leromandie.ch/agenda/",
        "https://leromandie.ch/programme/",
        "https://leromandie.ch/",
    ]),
    ("Le Bourg", [
        "https://le-bourg.ch/programme/",
        "https://le-bourg.ch/agenda/",
        "https://le-bourg.ch/",
    ]),
    ("D! Club", [
        "https://dclub.ch/events/",
        "https://dclub.ch/agenda/",
        "https://dclub.ch/",
    ]),
    ("Great Escape", [
        "https://www.the-great.ch/",
        "https://thegreatescape.ch/",
    ]),
    ("Bleu Lézard", [
        "https://www.bleu-lezard.ch/programme/",
        "https://www.bleu-lezard.ch/agenda/",
        "https://www.bleu-lezard.ch/",
    ]),
    ("Datcha", [
        "https://www.datcha.ch/",
        "https://datcha.ch/",
    ]),
    ("Resident Advisor", [
        "https://ra.co/events/ch/lausanne",
    ]),
    ("Shotgun", [
        "https://shotgun.live/fr/cities/lausanne",
    ]),
]


def _count_jsonld_events(soup: BeautifulSoup) -> int:
    count = 0
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if "Event" in str(item.get("@type", "")):
                count += 1
            for graph_item in item.get("@graph", []) or []:
                if isinstance(graph_item, dict) and "Event" in str(graph_item.get("@type", "")):
                    count += 1
    return count


def probe(url: str) -> dict:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException as exc:
        return {"error": str(exc)[:80]}

    soup = BeautifulSoup(resp.text, "lxml")
    return {
        "status": resp.status_code,
        "final_url": resp.url,
        "size": len(resp.text),
        "jsonld_events": _count_jsonld_events(soup),
        "next_data": bool(soup.find("script", id="__NEXT_DATA__")),
        "articles": len(soup.find_all("article")),
    }


def main() -> int:
    header = f"{'Venue':<18} {'URL':<55} {'HTTP':<5} {'Size':<8} {'JSON-LD':<8} {'NEXT':<5} {'<article>':<10}"
    print(header)
    print("-" * len(header))

    for name, urls in CANDIDATES:
        for url in urls:
            result = probe(url)
            if "error" in result:
                print(f"{name:<18} {url[:54]:<55} ERR   {result['error']}")
                continue
            print(
                f"{name:<18} {url[:54]:<55} "
                f"{result['status']:<5} "
                f"{result['size']:<8} "
                f"{result['jsonld_events']:<8} "
                f"{('Y' if result['next_data'] else 'N'):<5} "
                f"{result['articles']:<10}"
            )
        print()

    print("Legend:")
    print("  HTTP 200 + JSON-LD > 0  → use default JSON-LD parser (best case)")
    print("  HTTP 200 + NEXT = Y     → SPA with hydration data, parse __NEXT_DATA__")
    print("  HTTP 200 + articles > 5 → write a per-site HTML parser")
    print("  HTTP 403/429            → bot blocked (Cloudflare/WAF), needs Playwright or API")
    print("  HTTP 404 / ERR          → URL is wrong or domain dead, find canonical URL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
