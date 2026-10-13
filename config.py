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
    # Adresses vérifiées le 13 octobre 2026 (tools/snapshot_pages.py).
    # Retirés parce qu'ils refusent les robots : ra.co, shotgun.live,
    # leromandie.ch, fondation-hermitage.ch. On ne force pas ; leurs
    # événements passent souvent par Lausanne Tourisme.
    SCRAPE_AGGREGATORS: tuple[str, ...] = (
        # Lu par sources/lausanne_tourisme.py : plus de mille événements,
        # bars et clubs compris (Barberousse, Base Bar, Folklor, Romandie...).
        "https://www.lausanne-tourisme.ch/fr/evenement/",
        "https://www.lausanne.ch/agenda-et-actualites/agenda",
        "https://plateforme10.ch/agenda/",
        "https://www.guidle.com/fr/evenements/lausanne",
    )

    # Listing pages whose events live on their own pages: follow the links
    # whose path matches the pattern and read each page's JSON-LD.
    DETAIL_LINK_PATTERNS: tuple[tuple[str, str], ...] = (
        ("guidle.com", r"^/fr/evenements/[^/]+_[A-Za-z0-9]+/?$"),
    )
    # Event pages read per source at each collection, one at a time.
    MAX_DETAIL_PAGES: int = int(os.environ.get("MAX_DETAIL_PAGES", "300"))
    SCRAPE_PAUSE_SECONDS: float = float(os.environ.get("SCRAPE_PAUSE", "0.3"))

    # ----- Tier 2: venue-specific (alternative & niche scenes) -----
    # Retirés : casinodemontbenon.ch et folklore-club.ch (le domaine
    # n'existe pas ; le Folklor Club n'a pas de site, il est sur Lausanne
    # Tourisme).
    SCRAPE_VENUES: tuple[str, ...] = (
        # Théâtre & danse
        "https://vidy.ch/fr/calendrier/",
        "https://arsenic.ch/",
        "https://www.tkm.ch/",
        "https://beaulieu-lausanne.com/agenda/?cat=theatre",
        "https://theatre-octogone.ch/saison/programme/",
        # Concerts & alternatif
        "https://www.docks.ch/programme/",
        "https://www.le-bourg.ch/",
        "https://chorus.ch/programme/",
        # Clubbing
        "https://dclub.ch/agenda/",
        "https://mad.ch/agenda/",
        # Musique classique
        "https://www.opera-lausanne.ch/",
        "https://www.ocl.ch/concerts/",
        # Musées
        "https://www.mcba.ch/agenda",
        "https://elysee.ch/agenda/",
        "https://mudac.ch/agenda/",
        # Cinéma
        "https://www.cinematheque.ch/",
        "https://www.cinemabellevaux.ch/programme",
        "https://www.zinema.ch/",
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
