"""Flask application entry point — routes and bootstrap."""
from __future__ import annotations

import logging
import os
import secrets
import time
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS

import agenda
import db
import scraper
from config import config
from seed_data import build_demo_events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


DEMO_SOURCE = "seed"


def ensure_demo_events() -> None:
    """Keep the fictional demo programme dated from today.

    Demo events are only written when no collected event exists, and are
    rewritten once a day so the page never shows a stale, all-past demo.
    """
    if db.count_events(exclude_source=DEMO_SOURCE) > 0:
        return
    today = agenda.today_local()
    written = db.oldest_update(DEMO_SOURCE)
    if written and agenda.today_local(datetime.fromtimestamp(written, agenda.TZ)) == today:
        return
    db.delete_source(DEMO_SOURCE)
    events = build_demo_events(today)
    db.bulk_upsert(events, source=DEMO_SOURCE)
    logger.info("Wrote %d demo events dated from %s", len(events), today)


def bootstrap_database() -> None:
    """Initialize schema and make sure there is something to show."""
    db.init_db()
    ensure_demo_events()


def maybe_refresh_from_scraper() -> None:
    """Run a scrape pass if the cache TTL has expired, non-blocking-friendly."""
    age = time.time() - db.last_scrape_time()
    if age < config.SCRAPE_INTERVAL_SECONDS:
        return
    try:
        count = scraper.refresh_database()
        logger.info("Scraper refresh produced %d events", count)
    except Exception:
        logger.exception("Scraper refresh failed; falling back to existing data")


def _check_auth(username: str, password: str) -> bool:
    expected_user = os.environ.get("BASIC_AUTH_USER", "")
    expected_pass = os.environ.get("BASIC_AUTH_PASS", "")
    return (
        secrets.compare_digest(username, expected_user)
        and secrets.compare_digest(password, expected_pass)
    )


def _auth_required_response() -> Response:
    return Response(
        "Authentification requise.\n", 401,
        {"WWW-Authenticate": 'Basic realm="Lausanne Cultura"'},
    )


def create_app() -> Flask:
    """Application factory."""
    app = Flask(__name__)
    CORS(app)

    bootstrap_database()

    auth_enabled = bool(
        os.environ.get("BASIC_AUTH_USER") and os.environ.get("BASIC_AUTH_PASS")
    )

    @app.before_request
    def gate():
        if not auth_enabled:
            return None
        if request.path == "/api/health":
            return None
        creds = request.authorization
        if not creds or not _check_auth(creds.username or "", creds.password or ""):
            return _auth_required_response()
        return None

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    @app.route("/api/events")
    def api_events():
        maybe_refresh_from_scraper()
        ensure_demo_events()
        search = request.args.get("search", "").strip()

        # Collected events win; demo events only show when nothing was collected.
        events = db.list_all_events(exclude_source=DEMO_SOURCE)
        demo = not events
        if demo:
            events = db.list_all_events()
        if search:
            events = [e for e in events if agenda.matches(e, search)]

        programme = agenda.build_programme(events, agenda.today_local())
        last = db.last_scrape_time()
        return jsonify({
            **programme,
            "search": search,
            "total": len(programme["events"]),
            "demo": demo,
            "rubrics": list(agenda.RUBRIC_ORDER),
            "small_price_chf": agenda.SMALL_PRICE_CHF,
            "last_update": datetime.fromtimestamp(last, agenda.TZ).isoformat() if last else None,
            "source_count": len(config.SCRAPE_SOURCES),
        })

    @app.route("/api/categories")
    def api_categories():
        return jsonify({
            "categories": db.list_categories(),
            "all": list(config.CATEGORIES),
        })

    @app.route("/api/refresh", methods=["POST", "GET"])
    def api_refresh():
        try:
            count = scraper.refresh_database()
            return jsonify({
                "ok": True,
                "scraped": count,
                "total": db.count_events(),
            })
        except Exception as exc:
            logger.exception("Manual refresh failed")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/health")
    def api_health():
        return jsonify({
            "status": "ok",
            "events_in_db": db.count_events(),
            "last_scrape": db.last_scrape_time(),
        })

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(_err):
        return jsonify({"error": "internal server error"}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
