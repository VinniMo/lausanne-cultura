---
version: 1
slug: "templates-index-html"
primary_target: "templates/index.html"
related_targets: ["static/css/style.css","static/js/main.js"]
---

# Accueil : agenda du moment

## Scope
Page d'accueil `templates/index.html` (+ `static/css/style.css`, `static/js/main.js`). Mode : Operate. Construction code-led (sans comp). Référence validée : `.impeccable/mocks/decision/brief-accueil.md`, esquisses `v6-liste-archivo.html` (vue Liste, défaut) et `v6-affiches-archivo.html` (vue Affiches), `board-final.png`.

## Audience, tâche
Jeunes Lausannois sur téléphone : trouver en quelques secondes un plan pour ce soir ou ce week-end, l'ouvrir, le partager. Données collectées incomplètes : jamais de valeur inventée.

## Décisions confirmées (12.10.2026)
- Rubriques : Musique → Concerts ; Clubbing → Soirées & clubs ; Théâtre, Danse, Humour → Scène ; Cinéma → Cinéma ; Exposition → Expos ; le reste (Festival, Famille, Conférence, Sport, Atelier, Marché, Culture) → Autres.
- « Petit prix » : gratuit, ou prix le plus bas connu ≤ CHF 15 ; prix inconnu exclu du filtre.

## Direction contract
THESIS: Un programme du moment, pas une vitrine. La page répond « que faire ce soir ? » par une liste horaire groupée par jour puis par rubrique ; elle refuse les rails de cartes photo par discipline et le hero à slogan de la catégorie.
OWN-WORLD: Fond clair #f6f4ef, encre #151515, barre noire avec « Cultura » en rose #ff2e88. Archivo partout, tailles de lecture. Rubriques en petites étiquettes inclinées (-1.5°) : #a3004f sur #ffd9ea, #ffe500 sur noir, noir sur #ffe500. « GRATUIT » en étiquette jaune. Filets pointillés entre lignes, onglets soulignés rose, pastilles à bord noir 1.5px. Pas de bandeau pleine largeur, pas de grand chiffre, pas d'Anton, pas de noir sur rose fluo, clair par défaut.
STORY: Le visiteur voit tout de suite ce soir, compte par onglet ; il filtre (Pour moi, Gratuit / petit prix), ouvre une fiche en panneau bas, partage ou masque un lieu ; ce qui est masqué reste signalé et récupérable.
FIRST VIEWPORT: Mobile 390 : barre noire (logo à gauche ; loupe et « Mes goûts » à droite), onglets Ce soir · Demain · Week-end · Plus tard avec comptes, rangée de filtres + bascule Liste/Affiches, titre du jour 22px avec « N masqués · afficher », puis rubriques en étiquettes et ~7 lignes heure | titre + détail italique | lieu + prix à droite.
FORM: Liste-programme imprimée (v6 Archivo), choix direct de l'utilisateur après deux tirages dégradés ; signature : étiquettes de rubrique inclinées colorées ; interaction signature : panneau bas de fiche avec partage et « Masquer ce lieu ». seed: none (unavailable)
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Ouvert
Nom (Lausanne Cultura / LSN.live) ; périmètre (Lausanne ou région) ; étiquette « petit lieu » seulement si les données la fournissent.
