---
target: page d accueil (templates/index.html)
total_score: 16
max_score: 40
na_heuristics: 
p0_count: 2
p1_count: 2
target_identity: "file:/home/user/lausanne-cultura/templates/index.html"
target_fingerprint: "sha256:da3d3db16dcf53840d738bb4d96b1ba4bc06dc511d58c8f6c9be5e949c853859"
target_path: /home/user/lausanne-cultura/templates/index.html
timestamp: 2026-10-12T18-07-54Z
slug: templates-index-html
---
Méthode : double évaluation (A : revue de design · B : détecteur automatique), par deux sous-agents isolés, puis synthèse.
Conditions : données de démonstration (25 événements fictifs). Le réseau du conteneur bloque les photos (Unsplash) et les 27 sources ; les vraies données n'ont pas pu être testées. A a simulé des photos pour juger le rendu prévu.

## Score de santé du design

Mode retenu : Opérer (le visiteur accomplit une tâche : trouver quoi faire ce soir). La page est mise en scène comme une vitrine.

| # | Heuristique | Note | Problème principal |
|---|---|---|---|
| 1 | Visibilité de l'état du système | 2 | Chargement et filtre actif signalés ; compteurs figés, résultats hors écran, panne affichée comme « aucun résultat » |
| 2 | Correspondance avec le monde réel | 2 | Dates sans jour ni année, rails non chronologiques, « Voir détails » comme prix |
| 3 | Contrôle et liberté | 2 | Fermer la recherche garde la requête, pas de « Effacer », filtres perdus au rechargement |
| 4 | Cohérence | 2 | Lieu « Lausanne » sur la carte mais vide dans la fiche ; heure sur certaines cartes seulement |
| 5 | Prévention des erreurs | 1 | 24 événements passés sur 25 présentés comme actuels ; recherche sensible aux accents |
| 6 | Reconnaître plutôt que se souvenir | 2 | Heure et prix absents des cartes : ouvrir chaque fiche et mémoriser |
| 7 | Flexibilité et efficacité | 1 | Pas de filtre par date, pas de tri, pas de lien partageable, cartes inaccessibles au clavier |
| 8 | Esthétique et sobriété | 2 | Typo soignée ; slogan sur tout le premier écran, 12 rails empilés (6 900 px sur mobile) |
| 9 | Récupération des erreurs | 1 | Panne serveur = « 0 événements » + message qui accuse l'utilisateur, pas de « Réessayer » |
| 10 | Aide et documentation | 1 | Rien sur l'origine et la fraîcheur des données ; une seule source créditée sur 27 |
| **Total** | | **16/40** | **Faible** |

## Verdict de spécificité
Non spécifique : kit « agenda éditorial premium » générique (encre/crème, serif avec mot italique doré, ligne en capitales espacées, pastilles, rails, cartes photo, badge pulsant). Rien ne répond au brief : pas d'entrée ce soir/ce week-end, aucune distinction institution/petit lieu, organisation par discipline comme l'agenda officiel, ton institutionnel.
Détecteur : fichier template = 1 alerte fausse (flat-type-hierarchy, feuille de style Jinja non lue). Page affichée = 22 (mobile) / 30 (ordinateur) alertes, surtout une règle répétée : mois des dates en 9 px, contraste 2,7:1. Aussi : Inter 53 % du texte, point pulsant, eyebrow en capitales, tirets cadratins (contenu démo). Faux positifs : flat-type-hierarchy, italic-serif-display (seul « culture » est en italique). Le détecteur ne voit pas les problèmes majeurs (événements passés, clavier, image noire).

## Ce qui fonctionne
1. Fiche détaillée en panneau bas sur mobile (Date/Lieu/Tarif, Échap, tap hors fenêtre).
2. Étiquette de date des cartes (gros chiffre serif).
3. Hygiène : couleurs par thème en tokens, squelette fidèle, prefers-reduced-motion, chips = vrais boutons avec focus visible.

## Problèmes prioritaires
1. [P0] Aucun axe temporel ; événements passés présentés comme actuels ; démo non signalée. Fix : filtre serveur (date de fin incluse), tri chronologique, structure Ce soir/Demain/Ce week-end/Plus tard, jour+heure sur chaque carte, label démo. Commande : shape puis layout.
2. [P0 clavier/lecteur d'écran] Cartes non focusables, focus non piégé dans la fiche, pas d'aria-live ni aria-pressed. Fix : titre-lien couvrant la carte, dialog avec focus trap et retour du focus, région live. Commande : audit puis harden.
3. [P1] Sans photo, blocs noirs (FALLBACK_IMG : %23 double-encodé, main.js l.32) ; lieu inventé « Lausanne » ; « Voir détails » sans lien. Fix : carte typographique sans photo, masquer le bloc image vide, « non communiqué », corriger l'encodage. Commande : harden.
4. [P1] Premier écran = slogan ; « À ne pas manquer » = sélection inexistante menée par les institutions ; ton institutionnel ; clubbing rangé en Musique. Fix : « Ce soir à Lausanne · N plans » + sélecteur de jour, rail « Petits lieux ce week-end » fondé sur une règle, textes directs. Commande : distill puis clarify.
5. [P2] Recherche/filtres sans retour visible (résultats ~1 000 px plus bas), compteurs figés, requête fantôme, accents. Fix : replier le haut de page, « N résultats · Effacer » en tête, vider à la fermeture, normaliser les accents, état d'erreur avec « Réessayer ». Commande : clarify + harden.

## Personas
- Casey (mobile pressée) : rien d'exploitable au premier écran, loupe hors de portée du pouce, fermeture 40 px, filtres perdus, heure/prix absents.
- Jordan (première visite) : fausse sélection, recherche icône seule, pastille de compteur qui semble cliquable, date sans année, « Voir détails » sans issue.
- Riley (testeur) : panne = 0 événements, requête fantôme, accents, lieu incohérent, « — » pour date manquante, image noire, skip-link visible sur 1 px, décalage UTC possible (code).
- Léa, 23 ans (PRODUCT.md) : pas de « Ce soir », pas d'heure/prix, « bar » renvoie Vivaldi et La Traviata, ni type de lieu ni quartier, Clubbing absent, sélection musées/Opéra, pas de partage.

## Observations mineures
Eyebrow terminé par « · » orphelin ({{ "" }}) ; barre de filtres fixe qui coupe les titres de section ; mois 9 px à 2,7:1 ; rails courts laissant 2/3 de vide sur ordinateur, pas de flèches ; thème répété sur chaque carte ; champ de recherche sans étiquette ; badge pulsant sur événements d'avril ; pied de page « scrapé en temps réel » (jargon, inexact) et « Conception artisanale » (vide) ; Inter peu distinctive.

## Questions à se poser
1. Pourquoi organiser par discipline plutôt que par moment, si la réponse doit venir en quelques secondes ?
2. Un rail honnête « Ce week-end dans les petits lieux » ne servirait-il pas mieux le positionnement ?
3. À quoi ressemblerait une carte où lieu, heure et prix sont le visuel ? À qui parle vraiment ce registre magazine serif sombre ?
