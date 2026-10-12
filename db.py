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
    featured    INTEGER DEFAULT 0,
    source      TEXT DEFAULT 'fallback',
    scraped_at  REAL,
    updated_at  REAL
);

CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_date     ON events(date);
CREATE INDEX IF NOT EXISTS idx_events_featured ON events(featured);

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


def upsert_event(evt: dict, source: str = "scraper") -> None:
    """Insert or update an event keyed on its id."""
    now = time.time()
    tags = json.dumps(evt.get("tags", []), ensure_ascii=False)
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO events (id, title, date, time, end_date, location, address,
                                category, subcategory, description, image, price, url,
                                tags, featured, source, scraped_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title, date=excluded.date, time=excluded.time,
                end_date=excluded.end_date, location=excluded.location,
                address=excluded.address, category=excluded.category,
                subcategory=excluded.subcategory, description=excluded.description,
                image=excluded.image, price=excluded.price, url=excluded.url,
                tags=excluded.tags, featured=excluded.featured,
                source=excluded.source, updated_at=excluded.updated_at
        """, (
            evt.get("id"), evt.get("title", ""), evt.get("date", ""),
            evt.get("time", ""), evt.get("end_date", ""), evt.get("location", ""),
            evt.get("address", ""), evt.get("category", ""), evt.get("subcategory", ""),
            evt.get("description", ""), evt.get("image", ""), evt.get("price", ""),
            evt.get("url", ""), tags, 1 if evt.get("featured") else 0,
            source, now, now,
        ))


def bulk_upsert(events: list[dict], source: str = "scraper") -> None:
    """Upsert many events under the same source label."""
    for evt in events:
        upsert_event(evt, source=source)


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["tags"] = json.loads(d.get("tags") or "[]")
    except Exception:
        d["tags"] = []
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
