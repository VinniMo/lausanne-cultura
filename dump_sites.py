"""Fetch each working source and save the raw HTML to samples/ so Claude can
inspect the real markup and write per-site parsers.

Usage (run in Codespaces):
    python dump_sites.py
    git add samples/
    git commit -m "samples: dump source HTML for parser development"
    git push

Once pushed, Claude reads samples/*.html and writes parsers/<site>.py.
"""
from __future__ import annotations

from pathlib import Path

import requests

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

# Only the URLs that returned HTTP 200 in the probe.
SOURCES: list[tuple[str, str]] = [
    ("lausanne_tourisme", "https://www.lausanne-tourisme.ch/en/where-to-go-out-in-lausanne/"),
    ("romandie",          "https://www.leromandie.ch/"),
    ("le_bourg",          "https://www.lebourg.ch/"),
    ("folklor",           "https://folklor.club/"),
    ("datcha",            "https://datcha.ch/"),
    ("greatescape",       "https://greatescape.ch/"),
    ("punkbar",           "https://punkbar.ch/events/"),
    ("chauderon18",       "https://chauderon18.ch/"),
]

OUT_DIR = Path("samples")
OUT_DIR.mkdir(exist_ok=True)


def main() -> None:
    print(f"{'Slug':<20} {'Bytes':>8}  Path")
    print("-" * 60)
    for slug, url in SOURCES:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            path = OUT_DIR / f"{slug}.html"
            path.write_text(resp.text, encoding="utf-8")
            print(f"{slug:<20} {len(resp.text):>8}  {path}  (HTTP {resp.status_code})")
        except requests.RequestException as exc:
            print(f"{slug:<20}      ERR  {exc}")


if __name__ == "__main__":
    main()
