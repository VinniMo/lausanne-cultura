"""Flask application entry point — routes and bootstrap."""
from __future__ import annotations

import logging
import time

from flask import Flask, jsonify, render_template, request
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


def create_app() -> Flask:
    """Application factory."""
    app = Flask(__name__)
    CORS(app)

    bootstrap_database()

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
