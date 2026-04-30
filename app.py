"""Flask application entry point — routes and bootstrap."""
from __future__ import annotations

import logging
import os
import secrets
import time
from functools import wraps

from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS

import db
import scraper
from config import config
from seed_data import FALLBACK_EVENTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def bootstrap_database() -> None:
    """Initialize schema and ensure the DB has at least the fallback dataset."""
    db.init_db()
    if db.count_events() == 0:
        db.bulk_upsert(FALLBACK_EVENTS, source="seed")
        logger.info("Seeded database with %d fallback events", len(FALLBACK_EVENTS))


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
        category = request.args.get("category", "").strip()
        search = request.args.get("search", "").strip()
        events = db.list_events(category=category, search=search)
        return jsonify({
            "events": events,
            "total": len(events),
            "categories": list(config.CATEGORIES),
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
            "scrape_interval_seconds": config.SCRAPE_INTERVAL_SECONDS,
            "sources": db.latest_scrape_per_source(),
            "configured_sources": list(config.SCRAPE_SOURCES),
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
