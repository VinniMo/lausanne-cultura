"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "5000"))
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "1") == "1"

    DB_PATH: str = os.environ.get(
        "LAUSANNE_DB",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "events.db"),
    )

    SCRAPE_INTERVAL_SECONDS: int = int(os.environ.get("SCRAPE_INTERVAL", "3600"))
    SCRAPE_TIMEOUT_SECONDS: int = int(os.environ.get("SCRAPE_TIMEOUT", "20"))
    SCRAPE_USER_AGENT: str = os.environ.get(
        "SCRAPE_USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36",
    )

    # Priority sources — validated via probe_sources.py.
    # Each entry: (display_name, url). Multiple URLs per venue can be listed
    # if the canonical agenda page is uncertain — probe will tell us which.
    SCRAPE_SOURCES_PRIORITY: tuple[tuple[str, str], ...] = (
        ("Lausanne Tourisme", "https://www.lausanne-tourisme.ch/en/where-to-go-out-in-lausanne/"),
        ("Romandie",          "https://www.leromandie.ch/"),
        ("Le Bourg",          "https://www.lebourg.ch/"),
        ("Folklor Club",      "https://folklor.club/"),
        ("Datcha",            "https://datcha.ch/"),
        ("Great Escape",      "https://greatescape.ch/"),
        ("Continuum Club",    "https://continuumclub.ch/"),
        ("Punk Bar",          "https://punkbar.ch/"),
        ("Chauderon 18",      "https://chauderon18.ch/"),
    )

    @property
    def SCRAPE_SOURCES(self) -> tuple[str, ...]:
        return tuple(url for _, url in self.SCRAPE_SOURCES_PRIORITY)

    CATEGORIES: tuple[str, ...] = (
        "Musique", "Théâtre", "Exposition", "Cinéma", "Danse",
        "Festival", "Famille", "Conférence", "Sport", "Humour",
        "Atelier", "Marché", "Clubbing",
    )


config = Config()
