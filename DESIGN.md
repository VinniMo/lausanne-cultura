---
name: Lausanne Cultura
description: Le programme culturel du moment à Lausanne, lu comme une liste horaire imprimée.
colors:
  ground: "#f6f4ef"
  paper: "#ffffff"
  ink: "#151515"
  muted: "#5b5a57"
  dot: "#c4c0b7"
  line: "#dedad1"
  fluo: "#ff2e88"
  yellow: "#ffe500"
  rose-ink: "#a3004f"
  rose-pale: "#ffd9ea"
typography:
  headline:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "24px"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "22px"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  item:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: 1.25
  body:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  detail:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.3
  tag:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 800
    lineHeight: 1.3
  label:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.3
    fontFeature: "tnum"
rounded:
  none: "0px"
  field: "8px"
  toast: "10px"
  sheet: "16px"
  pill: "999px"
spacing:
  gutter: "16px"
  gutter-wide: "24px"
  wrap: "880px"
  row-y: "9px"
  gap-sm: "8px"
  gap-md: "14px"
components:
  bar:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    padding: "10px 16px"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "44px"
  button-secondary-hover:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.ink}"
  chip:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 11px"
    height: "32px"
  chip-active:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.ink}"
  segmented-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.field}"
    height: "29px"
  tab:
    textColor: "{colors.muted}"
    padding: "2px 0 9px"
  tab-selected:
    textColor: "{colors.ink}"
  tag-rose:
    backgroundColor: "{colors.rose-pale}"
    textColor: "{colors.rose-ink}"
    typography: "{typography.tag}"
    rounded: "{rounded.none}"
    padding: "3px 9px 4px"
  tag-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.yellow}"
    typography: "{typography.tag}"
    rounded: "{rounded.none}"
    padding: "3px 9px 4px"
  tag-yellow:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.ink}"
    typography: "{typography.tag}"
    rounded: "{rounded.none}"
    padding: "3px 9px 4px"
  tag-free:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 5px"
  input-search:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "0 12px"
    height: "42px"
  tile:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "7px 9px 9px"
  sheet:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sheet}"
    padding: "22px 16px 24px"
  toast:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.toast}"
    padding: "8px 8px 8px 16px"
---

# Design System: Lausanne Cultura

## Overview

**Creative North Star: "Le programme imprimé du soir"**

Lausanne Cultura se lit comme une feuille de programme qu'on aurait ramassée à l'entrée d'une salle : fond papier clair, encre noire, une liste horaire serrée, et quelques étiquettes de couleur collées de travers pour dire de quoi on parle. Rien n'est vitrine. La page répond à « que faire ce soir ? » par des lignes heure | titre | lieu, groupées par jour puis par rubrique, avec une densité de lecture et non d'affiche.

La couleur ne remplit jamais une surface de contenu : elle tient dans des étiquettes, un soulignement d'onglet, un mot du logo. Le noir porte la structure (barre du haut, filets de 1,5px, pastilles à bord noir), le jaune signale l'état actif ou la gratuité, le rose identifie la marque. Une seule famille, Archivo, à des tailles de lecture ; la hiérarchie vient de la graisse (400 à 800), pas de la taille.

Rejets confirmés par l'utilisateur : bandeaux de couleur pleine largeur dans le contenu, très grands chiffres ou titres, la police Anton, texte noir sur rose fluo, mode sombre par défaut.

**Key Characteristics:**
- Fond clair #f6f4ef par défaut, encre #151515, barre noire en tête.
- Archivo seule, de 12px à 24px, graisses 400 à 800.
- Étiquettes de rubrique inclinées (-1.5°) en trois styles fixes.
- Filets pointillés entre les lignes, traits pleins 1.5px pour la structure.
- Formes carrées pour les contenus, pilules pour les actions.

## Colors

Une palette papier-encre, réchauffée d'un gris sable, relevée par deux couleurs vives utilisées en petites surfaces seulement.

### Primary
- **Rose Cultura** (fluo): le mot « Cultura » dans la barre noire, le soulignement de 4px de l'onglet actif, le curseur du champ de recherche, l'anneau de focus du sélecteur Liste/Affiches. Toujours sur noir ou en trait ; jamais en fond sous du texte.

### Secondary
- **Jaune Affiche** (yellow): état actif des pastilles de filtre, étiquette « GRATUIT », survol des boutons secondaires, sélection de texte, heure posée sur l'image d'une affiche, anneau de focus dans la barre noire. Le jaune dit « actif » ou « gratuit », rien d'autre.

### Tertiary
- **Rose Encre** (rose-ink) sur **Rose Pâle** (rose-pale): le premier style d'étiquette de rubrique ; le rose encre seul nomme aussi le genre sous le nom du lieu dans une affiche typographique.

### Neutral
- **Sable Clair** (ground): fond de page, de la barre d'onglets collante, des panneaux bas.
- **Papier** (paper): champs, tuiles d'affiche, encart de première visite, survol des lignes ; aussi le texte et les bords blancs dans la barre noire.
- **Encre** (ink): texte, barre du haut, bords 1.5px, bouton principal, toast, deuxième style d'étiquette.
- **Gris Note** (muted): détails, comptes, prix, onglets inactifs, textes d'aide (contraste suffisant sur le fond sable).
- **Pointillé** (dot): filets pointillés de 1px entre lignes et faits de la fiche, poignée du panneau, barre de défilement.
- **Filet** (line): blocs de chargement (squelette).

### Named Rules
**La règle de l'étiquette.** La couleur vive vit dans des étiquettes, des traits et un mot ; aucune surface de contenu, aucune bande pleine largeur n'est peinte en rose ou en jaune. La seule bande pleine largeur est la barre noire du haut.

**La règle du rose sur noir.** Le rose fluo ne reçoit jamais de texte noir ; il se pose sur l'encre (logo) ou s'emploie comme trait.

**La règle du clair par défaut.** Le fond est clair ; le noir ne couvre que la barre, le bouton principal, le toast et l'étiquette encre.

## Typography

**Display Font:** aucune ; pas de police d'affichage.
**Body Font:** Archivo (auto-hébergée, variable 400 à 800, italique 400 ; repli system-ui, -apple-system, Segoe UI, sans-serif)

**Character:** Une grotesque compacte et franche, typée affiche mais tenue aux tailles de lecture ; l'italique sert aux détails comme une ligne de programme.

### Hierarchy
- **Headline** (800, 24px, 1.15, -0.01em): titre d'une fiche ou d'un panneau. C'est le plus grand texte du site.
- **Title** (800, 22px, 1.2): titre du jour (« Lundi 12 octobre »), première lettre capitalisée. Variantes à 20px (états vides et erreurs, logo) et 18px (encart de première visite, nom du lieu dans une affiche typographique).
- **Item** (700, 16px, 1.25): titre d'événement dans la liste ; 14.5px dans une tuile d'affiche. L'heure à côté est en 700, 15px, chiffres tabulaires.
- **Body** (400, 15px à 16px, 1.4 à 1.5): texte courant, description de fiche limitée à 65ch.
- **Detail** (400 italique, 13.5px, 1.3, muted): ligne de détail sous un titre.
- **Tag** (800, 14px, 1.3): étiquettes de rubrique et choix de goûts.
- **Label** (600 à 700, 12px à 15px): onglets (700, 15px), pastilles (600, 13px), comptes (12px, chiffres tabulaires), lieu et prix à droite (600, 14px / 400, 13px).

### Named Rules
**La règle des tailles de lecture.** Rien ne dépasse 24px. La hiérarchie passe par la graisse et l'encre, pas par l'échelle ; pas de grand chiffre, pas de titre géant.

**La règle d'une seule voix.** Archivo partout. Pas d'Anton, pas de seconde famille, pas de police système en affichage.

**La règle des chiffres alignés.** Heures, comptes et prix utilisent les chiffres tabulaires.

## Layout

Colonne unique centrée de 880px maximum (wrap), gouttière de 16px sur mobile et 24px dès 720px. La page empile : barre noire, recherche repliable, onglets collants (Ce soir · Demain · Week-end · Plus tard, avec compte), rangée de filtres avec le sélecteur Liste/Affiches poussé à droite, puis les jours, chacun découpé en rubriques.

Vue Liste : chaque événement est une ligne en grille de trois colonnes, heure (50px, 58px dès 720px) | titre et détail | lieu et prix alignés à droite (40vw max sur mobile, 220px dès 720px), padding vertical de 9px, séparée par un filet pointillé.

Vue Affiches : grille de tuiles à 2 colonnes (gap 10px), 3 dès 720px (gap 12px), 4 dès 1000px ; zone image de 92px puis 120px.

Rythme d'espacement serré et irrégulier par petits pas (6, 8, 10, 12, 14, 18px) : la densité est celle d'un programme, pas d'une page de présentation.

## Elevation & Depth

Système plat. La profondeur vient des traits d'encre de 1.5px et du contraste fond sable / papier blanc, pas des ombres. Deux ombres douces existent, liées à un état ou à un élément flottant.

### Shadow Vocabulary
- **Soulèvement de tuile** (`box-shadow: 0 6px 16px -10px rgba(21, 21, 21, 0.45)`): survol d'une tuile d'affiche seulement.
- **Toast** (`box-shadow: 0 8px 24px -8px rgba(21, 21, 21, 0.5)`): le toast flottant en bas d'écran.

Le panneau bas est posé sur un voile d'encre (`rgba(21, 21, 21, 0.55)`).

### Named Rules
**La règle du trait avant l'ombre.** Une surface se détache par un bord d'encre 1.5px ; l'ombre ne vient qu'en réponse au survol ou pour un élément flottant.

## Shapes

Deux familles de formes, sans mélange. Le contenu est carré (0px) : étiquettes, tuiles, encart de première visite, « GRATUIT ». Les actions sont arrondies : pilules (999px) pour boutons et pastilles, cercles pour les boutons icônes, 8px pour le champ de recherche et le sélecteur segmenté. Le panneau bas a des coins de 16px en haut (et sur les quatre coins dès 720px), le toast 10px.

Les bords sont en encre pleine de 1.5px ; les séparations de lignes en pointillé de 1px (dot). Le pointillé épais (1.5px dashed) marque un état non choisi ou provisoire. L'inclinaison de -1.5° est réservée aux étiquettes.

### Named Rules
**La règle de l'inclinaison.** Seules les étiquettes (rubriques, choix de goûts, marque « Démo ») sont inclinées, toujours de -1.5°. Lignes, tuiles, titres et boutons restent droits.

## Components

### Buttons
Des pilules franches à bord d'encre, lisibles au pouce.
- **Shape:** pilule (999px), hauteur 44px, bord 1.5px encre, 700 à 15px, icône SVG au trait de 16px possible.
- **Primary:** fond encre, texte blanc (« Valider », « Enregistrer », « Partager »). Survol : encre adoucie.
- **Secondary:** fond papier, texte encre ; survol en jaune.
- **Text button:** texte souligné (offset 3px), 600 à 14px, pour les actions secondaires (« Pas maintenant », « Masquer ce lieu », « Fermer »).
- **Focus:** anneau d'encre de 2.5px, décalé de 2px ; jaune dans la barre noire.

### Chips
- **Style:** pilule 32px, bord encre 1.5px, 600 à 13px, fond transparent ; survol papier.
- **State:** active en jaune avec texte 700 (« Pour moi », « Gratuit / petit prix »).
- **Segmented:** Liste/Affiches dans un cadre de 8px ; l'option active passe en encre et texte blanc.

### Cards / Containers
- **Tuile d'affiche:** carrée, fond papier, bord encre 1.5px ; zone image séparée par un trait d'encre, l'heure en étiquette jaune en haut à gauche. Sans image, la zone devient typographique : nom du lieu en 800 à 18px, genre en rose encre dessous.
- **Encart de première visite:** carré, fond papier, bord encre, padding 14px.
- **Shadow Strategy:** voir Elevation & Depth.

### Inputs / Fields
- **Style:** hauteur 42px, fond papier, bord encre 1.5px, rayon 8px, texte 16px, curseur rose.
- **Focus:** anneau d'encre de 2.5px décalé de 1px.

### Navigation
- **Barre:** pleine largeur, encre ; « Lausanne » blanc et « Cultura » rose, 800 à 20px ; à droite un bouton loupe circulaire de 40px et une pilule « Mes goûts », tous deux à bord blanc 1.5px, inversés en blanc au survol et à l'état ouvert.
- **Onglets:** collants en haut, sur fond sable avec un trait d'encre dessous ; 700 à 15px, gris au repos, encre et soulignement rose de 4px quand sélectionnés ; compte en 500 à 12px. Défilement horizontal sans barre visible.

### Étiquette de rubrique (signature)
Petite étiquette carrée, 800 à 14px, padding 3px 9px 4px, inclinée de -1.5°, suivie du compte en gris. Trois styles attribués dans l'ordre fixe des rubriques : rose encre sur rose pâle, jaune sur encre, encre sur jaune. Les mêmes styles reviennent dans la fiche (13px) et, à l'état choisi, dans les choix de « Mes goûts » ; un choix non retenu devient papier, texte gris, bord pointillé.

### Étiquette « GRATUIT »
Bloc jaune, texte encre 700 à 12.5px (12px dans une tuile), majuscules, droit, aligné sous le lieu. Un prix inconnu s'écrit « Prix n. c. » en gris : jamais de valeur inventée.

### Panneau bas (signature)
Fiche d'événement et « Mes goûts » s'ouvrent dans un dialogue collé en bas, 600px maximum, fond sable, coins hauts de 16px, poignée grise, bouton fermer de 44px. Les faits (Rubrique, Quand, Où, Prix) sont une grille libellé 56px | valeur, séparée par des pointillés. Entrée : glissement depuis le bas en 0.32s (cubic-bezier(0.16, 1, 0.3, 1)), désactivé si l'utilisateur réduit les animations. Dès 720px, le panneau flotte à 24px du bas, bordé sur quatre côtés.

### Toast
Pilule encre arrondie à 10px, texte blanc 600 à 14px, action en jaune soulignée (« Annuler »), centrée en bas.

## Do's and Don'ts

### Do:
- **Do** garder le fond clair #f6f4ef par défaut et la barre noire avec « Cultura » en #ff2e88.
- **Do** écrire tout en Archivo, entre 12px et 24px, et hiérarchiser par la graisse (400 à 800).
- **Do** signaler chaque rubrique par une étiquette inclinée de -1.5° dans l'un des trois styles : #a3004f sur #ffd9ea, #ffe500 sur #151515, #151515 sur #ffe500.
- **Do** marquer la gratuité par l'étiquette jaune « GRATUIT », et l'absence de donnée par « n. c. » en gris.
- **Do** tracer les structures en encre 1.5px et séparer les lignes par un pointillé de 1px.
- **Do** réserver le jaune à l'état actif et à la gratuité, le rose fluo au logo et aux traits d'état.
- **Do** utiliser les chiffres tabulaires pour heures, comptes et prix.

### Don't:
- **Don't** peindre de bande de couleur pleine largeur dans le contenu ; la barre noire du haut est la seule bande.
- **Don't** utiliser de très grands chiffres ni de titres au-delà de 24px.
- **Don't** utiliser la police Anton, ni une seconde famille.
- **Don't** poser du texte noir sur le rose fluo #ff2e88.
- **Don't** passer en mode sombre par défaut.
- **Don't** incliner autre chose que les étiquettes, ni arrondir les étiquettes et tuiles.
- **Don't** ajouter de surtitre ou d'étiquette décorative au-dessus d'un titre : une étiquette nomme une rubrique, un état ou une donnée.
