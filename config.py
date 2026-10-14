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
    SCRAPE_TIMEOUT_SECONDS: int = int(os.environ.get("SCRAPE_TIMEOUT", "12"))
    SCRAPE_USER_AGENT: str = os.environ.get(
        "SCRAPE_USER_AGENT",
        "Mozilla/5.0 (compatible; LausanneCultura/1.0; +https://github.com/VinniMo/lausanne-cultura)",
    )

    # Only sources the scraper can read today. SOURCES.md lists every source
    # audited live (13.10.2026): those waiting for a reader, with their
    # address and format, and those dropped, with the reason.

    # ----- Tier 1: aggregators (broad coverage, few sources) -----
    SCRAPE_AGGREGATORS: tuple[str, ...] = (
        # About 1,200 events in some 200 places, bars and small venues
        # included, all on one page (read by scraper.read_lausanne_tourisme).
        "https://www.lausanne-tourisme.ch/fr/evenement/",
    )

    # Listing pages whose events live on their own pages: follow the links
    # whose path matches the pattern and read each page's JSON-LD.
    # None in use at the moment (see SOURCES.md).
    DETAIL_LINK_PATTERNS: tuple[tuple[str, str], ...] = ()
    MAX_DETAIL_PAGES: int = int(os.environ.get("MAX_DETAIL_PAGES", "40"))

    # ----- Tier 2: venue-specific (complete the aggregators) -----
    # Listed after the aggregators: when both give the same event, the
    # venue's version is kept.
    SCRAPE_VENUES: tuple[str, ...] = (
        # Orchestre de Chambre de Lausanne: season calendar file (iCal).
        # Its name changes with each season.
        "https://www.ocl.ch/wp-content/uploads/2026/05/OCL_2026-2027_Saison_Complete.ics",
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
