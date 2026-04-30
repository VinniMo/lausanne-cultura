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

    # Default: 1 scrape par jour (86400s). Override via SCRAPE_INTERVAL si besoin.
    SCRAPE_INTERVAL_SECONDS: int = int(os.environ.get("SCRAPE_INTERVAL", "86400"))
    SCRAPE_TIMEOUT_SECONDS: int = int(os.environ.get("SCRAPE_TIMEOUT", "15"))
    SCRAPE_RETRIES: int = int(os.environ.get("SCRAPE_RETRIES", "2"))
    # UA Chrome réaliste — la majorité des CDN bloquent les UA "bot".
    SCRAPE_USER_AGENT: str = os.environ.get(
        "SCRAPE_USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    )

    # ----- Tier 1: aggregator (coverage large) -----
    SCRAPE_AGGREGATORS: tuple[str, ...] = (
        "https://www.lausanne-tourisme.ch/en/where-to-go-out-in-lausanne/",
    )

    # ----- Tier 2: bars, clubs, salles (testset minimal) -----
    SCRAPE_VENUES: tuple[str, ...] = (
        "https://www.leromandie.ch/",
        "https://www.lebourg.ch/",
        "https://punkbar.ch/",
        "https://chauderon18.ch/",
        "https://folklor.club/",
        "https://datcha.ch/",
        "https://greatescape.ch/",
    )

    @property
    def SCRAPE_SOURCES(self) -> tuple[str, ...]:
        """Combined source list: aggregators first (priority), then venues."""
        return self.SCRAPE_AGGREGATORS + self.SCRAPE_VENUES

    CATEGORIES: tuple[str, ...] = (
        "Musique", "Théâtre", "Exposition", "Cinéma", "Danse",
        "Festival", "Famille", "Conférence", "Sport", "Humour",
        "Atelier", "Marché", "Clubbing",
    )


config = Config()
