# Sources de données

Audit en direct du 13.10.2026 : chaque adresse a été appelée avec le
programme de collecte réel (plusieurs essais pour écarter les coupures du
réseau de test). Les efforts sont des estimations.

Sur les 29 sources configurées jusque-là, **aucune ne donnait d'événement
daté** : 4 sites inexistants ou perdus, 3 bloqués par une protection
anti-robot, 14 adresses fausses et 8 pages au format non lu. La lecture
« à l'aveugle » de la mise en page fabriquait en plus des faux événements
sans date (menus, titres de rubrique). Elle est supprimée : une page dans
un format inconnu ne donne plus rien.

## Sources actives (`config.py`)

| Source | Adresse | Format | Résultat | Limites |
|---|---|---|---|---|
| Lausanne Tourisme | https://www.lausanne-tourisme.ch/fr/evenement/ | Cartes HTML, toutes sur une page (lecteur `read_lausanne_tourisme`) | ~1 220 événements, ~200 lieux, dont bars et petits lieux (Jumeaux, Base Bar, Satellite, Barberousse, D! Club, MAD) | Ni heure ni prix dans la liste. Les rendez-vous réguliers sont donnés comme une période (« du 23.07 au 24.12 ») sans les jours de la semaine. Heure, jours et prix sont sur la fiche de chaque événement (`.js-openingHours[data-opening]`, bloc des prix) |
| OCL | https://www.ocl.ch/wp-content/uploads/2026/05/OCL_2026-2027_Saison_Complete.ics | Calendrier iCal | 47 concerts avec heure et lieu | Le nom du fichier change à chaque saison. Ni image, ni prix, ni les concerts en collaboration |

Lausanne Tourisme utilise la même base de données que l'agenda de la Ville
(environ 89 % de recouvrement sur un échantillon) : la Ville n'est donc pas
collectée à part. Un même événement annoncé par les deux sources est
fusionné (même jour, même lieu, un mot distinctif commun dans le titre) et
c'est la version du lieu qui est gardée.

## À brancher (lecteur à écrire)

La plupart de ces lieux figurent déjà sur Lausanne Tourisme ; un lecteur
dédié apporterait l'heure, le prix ou des soirées absentes.

| Source | Bonne adresse | Format | Effort |
|---|---|---|---|
| Vidy | https://vidy.ch/fr/calendrier/ | JSON intégré (`__NEXT_DATA__`, `props.pageProps.node.archive.eventDates`) | ≈ 1 h |
| Arsenic | https://arsenic.ch/wp-json/arsenic/v1/etickets/events?language=fr | API JSON | ≈ 1 h |
| TKM | https://www.tkm.ch/ | Cartes HTML (`a.row.representation`, date « 17.11–22.11.26 ») | ≈ 1 h |
| Théâtre de Beaulieu | https://beaulieu-lausanne.com/agenda/?cat=theatre (2 pages) | Cartes HTML (`article.excerpt-event`, date en toutes lettres) | ≈ 1 h |
| L'Octogone (Pully) | https://theatre-octogone.ch/saison/programme/ | Cartes HTML (`div.row.event`, « jeu. 29.10.2026 / 20h00 ») | ≈ 1 h |
| Les Docks | https://www.docks.ch/programme/ | Cartes HTML (date dans l'adresse `/YYYYMMDD/`) | ≈ 1 h |
| Le Romandie | https://www.leromandie.ch/programmation | Cartes HTML (« 16 oct. 2026 », « 23H00 ») | ≈ 1 h |
| Chorus | https://chorus.ch/programme/ | Cartes HTML (« 22 oct », sans année) | ≈ 1 h |
| D! Club | https://dclub.ch/agenda/ | Cartes HTML (`div.event[data-date=YYYYMMDD]`) | ≈ 1 h |
| MAD | https://www.mad.club/agenda/ | HTML Elementor (« jeudi 15 octobre 2026 ») | ≈ 1 h |
| Folklor | https://www.folklor.club/events/ | Cartes HTML (`article.event`, « 15.10.2026 ») | ≈ 1 h |
| Zinéma | API Sanity (`vle63mzm.api.sanity.io`, type `screening`) | API JSON, séances avec date, heure et salle | ≈ 1 h |
| Cinéma Bellevaux | https://www.cinemabellevaux.ch/ (pages par jour `/mardi-13-10-2026`) | HTML, séances avec date et heure | ≈ 1 h |
| Cinémathèque | https://live.cinematheque.ch/ (paginé) | HTML, séances avec date et heure | ½ journée |
| Opéra de Lausanne | https://www.opera-lausanne.ch/season/2026-27/ | Cartes HTML sans année ni heure, détail sur chaque fiche | ½ journée |
| Plateforme 10 (MCBA, Photo Elysée, mudac) | https://plateforme10.ch/wp-json/lausanne-musees/v1/get-events | API JSON (événements et expositions des 3 musées) | ≈ 1 h ; `Crawl-delay: 10` |
| Guidle | API interne `guidle.com/api/rest/2.0/portals/search-offers/…` | API JSON non documentée, fragile | ½ journée |

Plusieurs dates sont écrites en toutes lettres ou sans année : un lecteur de
dates françaises commun servirait à la plupart de ces lieux.

## Retirées

| Source | Raison |
|---|---|
| agenda.lausanne.ch | Le domaine n'existe pas. La vraie page de la Ville se charge en JavaScript (Algolia) et recoupe Lausanne Tourisme |
| lausanne.ch (page agenda) | Page introuvable (404) ; même agenda que ci-dessus |
| Resident Advisor (ra.co) | Protection anti-robot (DataDome, 403) |
| Shotgun | Protection anti-robot (Vercel, 429) |
| Fondation de l'Hermitage | Protection anti-robot (Cloudflare, 403) |
| Casino de Montbenon | Le domaine n'existe pas ; salle louée sans programme propre (ses événements sont sur Lausanne Tourisme) |
| Le Bourg (le-bourg.ch) | Domaine perdu, il sert un blog sans rapport ; aucun site actif trouvé |
| Folklore Club (folklore-club.ch) | Le domaine n'existe pas ; le vrai site est folklor.club (voir « À brancher ») |
| MCBA, Photo Elysée, mudac | Couverts par Plateforme 10 et par Lausanne Tourisme |

Les protections anti-robot ne sont pas contournées : Resident Advisor et
Shotgun, très utiles pour les soirées, demanderaient un accord ou une API
officielle.

## Règles de politesse

Beaucoup de ces sites demandent dans leur `robots.txt` d'attendre 10
secondes entre deux pages (`Crawl-delay: 10`). Le programme lit aujourd'hui
une seule page par source et par heure, ce qui reste dans ces limites ; il
faudra espacer les requêtes dès qu'un lecteur suivra des fiches détaillées.
