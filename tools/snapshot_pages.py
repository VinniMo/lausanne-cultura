"""Save a light copy of each page listed in tools/snapshot_urls.txt.

Used to write and test source-specific readers without network access from
the development machine: GitHub Actions runs this script, commits the copies
under snapshots/, and the developer pulls them.

For each URL: robots.txt is checked first (a refused page is not fetched),
then the page is fetched once with the collector's user agent. The copy
keeps the page structure and its data scripts (JSON-LD, JSON) but drops
styles, SVG and code. snapshots/INDEX.md lists the outcome of every URL and,
for each page, the links that look like an agenda.

Run with: python tools/snapshot_pages.py
"""
from __future__ import annotations

import os
import re
import sys
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, Comment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import config  # noqa: E402

URL_LIST = os.path.join(ROOT, "tools", "snapshot_urls.txt")
OUT_DIR = os.path.join(ROOT, "snapshots")
AGENDA_WORDS = re.compile(
    r"agenda|programm|event|evenement|événement|saison|concert|calendrier|spectacle|expo|soiree|soirée",
    re.IGNORECASE,
)
DATA_SCRIPT_TYPES = {"application/ld+json", "application/json"}
MAX_DATA_SCRIPT = 400_000


def read_urls() -> list[str]:
    with open(URL_LIST, encoding="utf-8") as fh:
        return [line.split("#")[0].strip() for line in fh if line.split("#")[0].strip()]


def file_name(url: str) -> str:
    parts = urlparse(url)
    slug = re.sub(r"[^a-z0-9]+", "-", f"{parts.path}?{parts.query}".lower()).strip("-")
    host = parts.netloc.lower().removeprefix("www.")
    return f"{host}__{slug or 'accueil'}.html"


_robots: dict[str, RobotFileParser | None] = {}


def robots_allows(url: str) -> bool:
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in _robots:
        parser = RobotFileParser()
        try:
            resp = requests.get(f"{base}/robots.txt", timeout=config.SCRAPE_TIMEOUT_SECONDS,
                                headers={"User-Agent": config.SCRAPE_USER_AGENT})
            parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
            _robots[base] = parser
        except requests.RequestException:
            _robots[base] = None  # unreachable robots.txt: no stated rule
    parser = _robots[base]
    return parser is None or parser.can_fetch(config.SCRAPE_USER_AGENT, url)


def lighten(html: str) -> str:
    """Keep the structure and data, drop presentation and code."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["style", "svg", "noscript", "iframe", "link", "template", "video", "audio"]):
        tag.decompose()
    for node in soup.find_all(string=lambda s: isinstance(s, Comment)):
        node.extract()
    for script in soup("script"):
        kind = (script.get("type") or "").lower()
        body = script.string or ""
        if kind in DATA_SCRIPT_TYPES or script.get("id") in ("__NEXT_DATA__", "__NUXT_DATA__"):
            if len(body) <= MAX_DATA_SCRIPT:
                continue
        script.string = f"/* {len(body)} caractères retirés */" if body else ""
    return str(soup)


def agenda_links(html: str, page_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    host = urlparse(page_url).netloc.lower().removeprefix("www.")
    seen: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        url = urljoin(page_url, a["href"]).split("#")[0]
        text = " ".join(a.get_text(" ", strip=True).split())[:60]
        if urlparse(url).netloc.lower().removeprefix("www.") != host:
            continue
        if AGENDA_WORDS.search(urlparse(url).path) or AGENDA_WORDS.search(text):
            if url not in [u for u, _ in seen]:
                seen.append((url, text))
    return seen[:15]


def snapshot(url: str) -> dict:
    row = {"url": url, "status": "", "final": "", "size": 0, "file": "", "links": []}
    try:
        if not robots_allows(url):
            row["status"] = "refusé par robots.txt"
            return row
        resp = requests.get(url, timeout=config.SCRAPE_TIMEOUT_SECONDS, headers={
            "User-Agent": config.SCRAPE_USER_AGENT,
            "Accept-Language": "fr-CH,fr;q=0.9,en;q=0.5",
        })
    except requests.RequestException as exc:
        row["status"] = f"erreur : {type(exc).__name__}: {str(exc)[:160]}"
        return row
    row["status"] = str(resp.status_code)
    row["final"] = resp.url if resp.url != url else ""
    row["size"] = len(resp.content)
    if resp.status_code == 200 and "html" in resp.headers.get("Content-Type", "html"):
        name = file_name(url)
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
            fh.write(lighten(resp.text))
        row["file"] = name
        row["links"] = agenda_links(resp.text, resp.url)
    return row


def index(rows: list[dict]) -> str:
    lines = ["# Copies de pages", "",
             "| Adresse | Réponse | Redirigée vers | Taille | Copie |", "|---|---|---|---:|---|"]
    for r in rows:
        size = f"{r['size'] // 1024} Ko" if r["size"] else ""
        lines.append(f"| {r['url']} | {r['status']} | {r['final']} | {size} | {r['file']} |")
    lines += ["", "## Liens qui ressemblent à un agenda", ""]
    for r in rows:
        if r["links"]:
            lines.append(f"**{r['url']}**")
            lines += [f"- {u} · {t}" for u, t in r["links"]]
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    for url in read_urls():
        rows.append(snapshot(url))
        print(f"{rows[-1]['status']:<6} {url}", flush=True)
    text = index(rows)
    with open(os.path.join(OUT_DIR, "INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text)


if __name__ == "__main__":
    main()
