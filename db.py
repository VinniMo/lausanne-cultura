"""SQLite persistence layer for Lausanne Cultura events."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator

from config import config

DB_PATH = config.DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    date        TEXT,
    time        TEXT,
    end_date    TEXT,
    location    TEXT,
    address     TEXT,
    category    TEXT,
    subcategory TEXT,
    description TEXT,
    image       TEXT,
    price       TEXT,
    url         TEXT,
    tags        TEXT,
    schedule    TEXT DEFAULT '',
    featured    INTEGER DEFAULT 0,
    source      TEXT DEFAULT 'fallback',
    scraped_at  REAL,
    updated_at  REAL
);

CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_date     ON events(date);
CREATE INDEX IF NOT EXISTS idx_events_featured ON events(featured);

-- What an event's own page adds to a listing (time, days, price, address),
-- kept so that each page is read again only when it gets old.
CREATE TABLE IF NOT EXISTS page_details (
    url        TEXT PRIMARY KEY,
    data       TEXT,
    checked_at REAL
);

CREATE TABLE IF NOT EXISTS scrape_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT,
    url        TEXT,
    status     TEXT,
    count      INTEGER,
    message    TEXT,
    timestamp  REAL
);
"""


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection that auto-commits on exit and always closes."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and indexes if they don't exist."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(events)")}
        if "schedule" not in columns:  # databases created before schedules
            conn.execute("ALTER TABLE events ADD COLUMN schedule TEXT DEFAULT ''")


def upsert_event(evt: dict, source: str = "scraper") -> None:
    """Insert or update an event keyed on its id.

    The event's own "source" (the site it was collected from) wins over the
    source argument, which labels events that do not name one.
    """
    now = time.time()
    tags = json.dumps(evt.get("tags", []), ensure_ascii=False)
    schedule = json.dumps(evt["schedule"]) if evt.get("schedule") else ""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO events (id, title, date, time, end_date, location, address,
                                category, subcategory, description, image, price, url,
                                tags, schedule, featured, source, scraped_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title, date=excluded.date, time=excluded.time,
                end_date=excluded.end_date, location=excluded.location,
                address=excluded.address, category=excluded.category,
                subcategory=excluded.subcategory, description=excluded.description,
                image=excluded.image, price=excluded.price, url=excluded.url,
                tags=excluded.tags, schedule=excluded.schedule, featured=excluded.featured,
                source=excluded.source, updated_at=excluded.updated_at
        """, (
            evt.get("id"), evt.get("title", ""), evt.get("date", ""),
            evt.get("time", ""), evt.get("end_date", ""), evt.get("location", ""),
            evt.get("address", ""), evt.get("category", ""), evt.get("subcategory", ""),
            evt.get("description", ""), evt.get("image", ""), evt.get("price", ""),
            evt.get("url", ""), tags, schedule, 1 if evt.get("featured") else 0,
            evt.get("source") or source, now, now,
        ))


def bulk_upsert(events: list[dict], source: str = "scraper") -> None:
    """Upsert many events (source labels those that do not name their own)."""
    for evt in events:
        upsert_event(evt, source=source)


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["tags"] = json.loads(d.get("tags") or "[]")
    except Exception:
        d["tags"] = []
    try:
        d["schedule"] = json.loads(d.get("schedule") or "[]")
    except Exception:
        d["schedule"] = []
    d["featured"] = bool(d.get("featured"))
    return d


def count_events(source: str | None = None, exclude_source: str | None = None) -> int:
    sql, params = "SELECT COUNT(*) AS n FROM events WHERE 1=1", []
    if source:
        sql += " AND source = ?"
        params.append(source)
    if exclude_source:
        sql += " AND source != ?"
        params.append(exclude_source)
    with get_conn() as conn:
        return conn.execute(sql, params).fetchone()["n"]


def list_all_events(exclude_source: str | None = None) -> list[dict]:
    sql, params = "SELECT * FROM events", []
    if exclude_source:
        sql += " WHERE source != ?"
        params.append(exclude_source)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_dict(r) for r in rows]


def oldest_update(source: str) -> float:
    """When rows from this source were last written (0 when there are none)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MIN(updated_at) AS ts FROM events WHERE source = ?", (source,)
        ).fetchone()
    return row["ts"] or 0.0


def delete_source(source: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM events WHERE source = ?", (source,))


def count_upcoming(source: str, today: str) -> int:
    """Events stored under this source that are not over (dates as YYYY-MM-DD)."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) AS n FROM events"
            " WHERE source = ? AND COALESCE(NULLIF(end_date, ''), date) >= ?",
            (source, today),
        ).fetchone()["n"]


def delete_unannounced(source: str, announced: set[str]) -> int:
    """Delete this source's events whose id is not announced. Returns how many."""
    with get_conn() as conn:
        rows = conn.execute("SELECT id FROM events WHERE source = ?", (source,)).fetchall()
        gone = [(r["id"],) for r in rows if r["id"] not in announced]
        conn.executemany("DELETE FROM events WHERE id = ?", gone)
    return len(gone)


def get_details(urls: list[str]) -> dict[str, tuple[float, dict]]:
    """Saved page details by URL: (time they were read, data)."""
    found: dict[str, tuple[float, dict]] = {}
    with get_conn() as conn:
        for start in range(0, len(urls), 500):  # SQLite caps the number of ? per query
            chunk = urls[start:start + 500]
            rows = conn.execute(
                f"SELECT url, data, checked_at FROM page_details WHERE url IN ({','.join('?' * len(chunk))})",
                chunk,
            ).fetchall()
            for row in rows:
                found[row["url"]] = (row["checked_at"], json.loads(row["data"] or "{}"))
    return found


def save_details(url: str, data: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO page_details (url, data, checked_at) VALUES (?, ?, ?)"
            " ON CONFLICT(url) DO UPDATE SET data=excluded.data, checked_at=excluded.checked_at",
            (url, json.dumps(data, ensure_ascii=False), time.time()),
        )


def list_categories() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS n FROM events WHERE category != '' GROUP BY category ORDER BY n DESC"
        ).fetchall()
    return [{"name": r["category"], "count": r["n"]} for r in rows]


def log_scrape(source: str, url: str, status: str, count: int, message: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO scrape_log (source, url, status, count, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (source, url, status, count, message, time.time()),
        )


def last_scrape_time(successful_only: bool = False) -> float:
    """Time of the last collection attempt (or last successful one)."""
    sql = "SELECT MAX(timestamp) AS ts FROM scrape_log"
    if successful_only:
        sql += " WHERE status = 'ok'"
    with get_conn() as conn:
        row = conn.execute(sql).fetchone()
    return row["ts"] or 0.0


def source_status() -> list[dict]:
    """Latest collection result for each source URL."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT l.url, l.status, l.count, l.message, l.timestamp
            FROM scrape_log l
            JOIN (SELECT url, MAX(id) AS id FROM scrape_log GROUP BY url) last
              ON last.id = l.id
        """).fetchall()
    return [dict(r) for r in rows]


def clear_events() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM events")
