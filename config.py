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

    # ----- Tier 1: aggregators (broad coverage, few sources) -----
    SCRAPE_AGGREGATORS: tuple[str, ...] = (
        "https://agenda.lausanne.ch/",
        "https://www.lausanne.ch/vie-pratique/culture-et-loisirs/agenda.html",
        "https://ra.co/events/ch/lausanne",
        "https://shotgun.live/fr/cities/lausanne",
        "https://plateforme10.ch/agenda",
    )

    # ----- Tier 2: venue-specific (alternative & niche scenes) -----
    SCRAPE_VENUES: tuple[str, ...] = (
        # Théâtre & danse
        "https://vidy.ch/programme",
        "https://arsenic.ch/saison",
        "https://tkm.ch/saison",
        "https://www.theatredebeaulieu.ch/programme",
        "https://www.theatre-octogone.ch/saison",
        # Concerts & alternatif
        "https://lesdocks.ch/agenda",
        "https://leromandie.ch/programme",
        "https://le-bourg.ch/programme",
        "https://www.chorus.ch/agenda",
        "https://casinodemontbenon.ch/agenda",
        # Clubbing
        "https://dclub.ch/events",
        "https://mad.ch/agenda",
        "https://folklore-club.ch/events",
        # Musique classique
        "https://www.opera-lausanne.ch/saison",
        "https://www.ocl.ch/concerts",
        # Musées
        "https://www.mcba.ch/expositions",
        "https://elysee.ch/expositions",
        "https://mudac.ch/expositions",
        "https://www.fondation-hermitage.ch/expositions",
        # Cinéma
        "https://www.cinematheque.ch/programme",
        "https://www.cinemabellevaux.ch/programme",
        "https://zinema.ch/programme",
    )

    CATEGORIES: tuple[str, ...] = (
        "Musique", "Théâtre", "Exposition", "Cinéma", "Danse",
        "Festival", "Famille", "Conférence", "Sport", "Humour",
        "Atelier", "Marché", "Clubbing",
    )

    @property
    def SCRAPE_SOURCES(self) -> tuple[str, ...]:
        """Combined source list: aggregators first (priority), then venues."""
        return self.SCRAPE_AGGREGATORS + self.SCRAPE_VENUES


config = Config()
