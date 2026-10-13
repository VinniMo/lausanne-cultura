"""Audit every configured source: does it answer, and how good are its events?

Fetches each source once (same rules as the live collection), writes nothing
to the database, and prints a Markdown report. On GitHub Actions the report
also goes to the run's summary page.

Run with: python tools/audit_sources.py
"""
from __future__ import annotations

import os
import sys
import time
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scraper  # noqa: E402
from agenda import parse_day, read_price, today_local  # noqa: E402
from config import config  # noqa: E402


def _share(events: list[dict], test) -> str:
    if not events:
        return "–"
    return f"{round(100 * sum(1 for e in events if test(e)) / len(events))} %"


def _is_upcoming(evt: dict, today) -> bool:
    start = parse_day(evt.get("date", ""))
    if start is None:
        return False
    end = parse_day(evt.get("end_date", "")) or start
    return max(start, end) >= today


def _this_week(evt: dict, today) -> bool:
    """On at least one of the next seven days (today included)."""
    start = parse_day(evt.get("date", ""))
    end = parse_day(evt.get("end_date", "")) or start
    return start is not None and start <= today + timedelta(days=6) and end >= today


def audit_one(url: str, today) -> dict:
    started = time.time()
    try:
        events, method = scraper.scrape_one(url)
        error = ""
    except Exception as exc:  # any failure is a finding, not a crash
        events, method, error = [], "erreur", str(exc)
    upcoming = [e for e in events if _is_upcoming(e, today)]
    return {
        "url": url,
        "method": method,
        "error": error,
        "found": len(events),
        "events": events,
        "upcoming": upcoming,
        "seconds": round(time.time() - started, 1),
    }


def verdict(row: dict) -> str:
    if row["error"]:
        return "ne répond pas"
    if not row["found"]:
        return "aucun événement"
    if not row["upcoming"]:
        return "rien d'utilisable"
    return "fonctionne"


def report(rows: list[dict], today) -> str:
    working = [r for r in rows if verdict(r) == "fonctionne"]
    unique = {e["id"] for r in rows for e in r["upcoming"]}
    week = {e["id"] for r in rows for e in r["upcoming"] if _this_week(e, today)}
    lines = [
        f"# Audit des sources ({today.isoformat()})",
        "",
        f"**{len(working)} source(s) sur {len(rows)}** donnent des événements à venir ; "
        f"**{len(unique)}** événements à venir distincts au total, dont "
        f"**{len(week)}** sur les sept prochains jours.",
        "",
        "Pourcentages calculés sur les événements à venir de chaque source.",
        "",
        "| Source | Verdict | Méthode | Trouvés | À venir | 7 jours | Heure | Lieu | Image | Prix | Non classés | Durée |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    order = {"fonctionne": 0, "rien d'utilisable": 1, "aucun événement": 2, "ne répond pas": 3}
    for r in sorted(rows, key=lambda r: (order[verdict(r)], -len(r["upcoming"]), r["url"])):
        up = r["upcoming"]
        lines.append(
            f"| {r['url']} | {verdict(r)} | {r['method']} | {r['found']} | {len(up)} "
            f"| {sum(1 for e in up if _this_week(e, today))} "
            f"| {_share(up, lambda e: e.get('time'))} "
            f"| {_share(up, lambda e: e.get('location'))} "
            f"| {_share(up, lambda e: e.get('image'))} "
            f"| {_share(up, lambda e: read_price(e.get('price', ''))['known'])} "
            f"| {_share(up, lambda e: e.get('category') == 'Culture')} "
            f"| {r['seconds']} s |"
        )

    lines += ["", "## Exemples par source", "",
              "Événements à venir, ou à défaut ce que la source a renvoyé.", ""]
    for r in rows:
        sample = r["upcoming"] or r["events"]
        if sample:
            lines.append(f"**{r['url']}**")
            for e in sample[:3]:
                when = f"{e.get('date')} {e.get('time') or ''}".strip() or "sans date"
                place = e.get("location") or "lieu inconnu"
                lines.append(f"- {when} · {e['title'][:70]} · {place[:40]}")
            lines.append("")

    failed = [r for r in rows if r["error"]]
    if failed:
        lines += ["## Erreurs", ""]
        lines += [f"- {r['url']} : {r['error'][:200]}" for r in failed]
    return "\n".join(lines) + "\n"


def main() -> None:
    today = today_local()
    rows = []
    for url in config.SCRAPE_SOURCES:
        rows.append(audit_one(url, today))
        print(f"{verdict(rows[-1]):<18} {len(rows[-1]['upcoming']):>4}  {url}", flush=True)

    text = report(rows, today)
    print("\n" + text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text)


if __name__ == "__main__":
    main()
