# Lausanne Cultura

> L'agenda culturel de Lausanne — scrapé en temps réel, classé par thème,
> pensé d'abord pour mobile.

Concerts, expositions, théâtre, danse, festivals, cinéma… Toute la vie culturelle
lausannoise dans une interface artistique, épurée et très visuelle.

## Stack

| Couche       | Choix                                                                    |
|--------------|--------------------------------------------------------------------------|
| Backend      | Flask 3 · application factory · SQLite (persistance)                     |
| Scraping     | `requests` + `BeautifulSoup` (JSON-LD prioritaire, fallback HTML)        |
| Frontend     | HTML5 sémantique · CSS mobile-first · Vanilla JS                         |
| Typographie  | Fraunces (serif éditorial) + Inter (UI)                                  |

## Architecture

```
.
├── app.py          # Flask factory + routes
├── config.py       # Config immuable (env vars)
├── db.py           # Couche SQLite (init, upsert, queries)
├── scraper.py      # Scraping JSON-LD + fallback HTML
├── seed_data.py    # Dataset de fallback (25 événements)
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/main.js
└── .devcontainer/
    └── devcontainer.json
```

## Endpoints

| Méthode | URL               | Rôle                                          |
|---------|-------------------|-----------------------------------------------|
| GET     | `/`               | Application                                   |
| GET     | `/api/events`     | Liste filtrable (`?category=…&search=…`)      |
| GET     | `/api/categories` | Catégories disponibles + comptes              |
| GET/POST| `/api/refresh`    | Force un scrape immédiat                      |
| GET     | `/api/health`     | Statut + nombre d'événements + dernier scrape |

## Lancer en local

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

Au premier démarrage, la base est initialisée et seedée avec le dataset de
fallback. Un scrape live s'exécute paresseusement quand la fenêtre TTL expire
(`SCRAPE_INTERVAL`, défaut 1h).

## Lancer dans GitHub Codespaces

1. Sur GitHub, ouvre le repo → **Code** → **Codespaces** → **Create codespace**.
2. Le devcontainer installe les dépendances et démarre Flask automatiquement.
3. Une notification *Open in Browser* apparaît pour le port 5000.

Pas besoin d'API key GitHub CLI — tout est piloté par
`.devcontainer/devcontainer.json`.

## Variables d'environnement

| Variable          | Défaut         | Description                       |
|-------------------|----------------|-----------------------------------|
| `HOST`            | `0.0.0.0`      | Adresse d'écoute Flask            |
| `PORT`            | `5000`         | Port HTTP                         |
| `FLASK_DEBUG`     | `1`            | Mode debug Flask                  |
| `LAUSANNE_DB`     | `./events.db`  | Chemin SQLite                     |
| `SCRAPE_INTERVAL` | `3600`         | TTL du cache scraping (secondes)  |
| `SCRAPE_TIMEOUT`  | `12`           | Timeout HTTP du scraper           |
| `APIFY_API_KEY`   | *(vide)*       | Token Apify (scraping avancé)     |

## Design

- **Mobile-first** — rails horizontaux avec scroll-snap, expérience comme
  un magazine qu'on feuillette du pouce.
- **Sobre & artistique** — palette ink/cream, Fraunces italique pour les
  titres, animations discrètes (`prefers-reduced-motion` respecté).
- **Image-forward** — chaque carte dominée par sa photo, texte en contrepoint.
- **Couleurs par thème** — chaque catégorie a son accent chromatique
  (terracotta pour Musique, sage pour Famille, mineral blue pour Exposition…).

## Licence

MIT.
