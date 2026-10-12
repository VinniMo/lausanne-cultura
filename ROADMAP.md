# Feuille de route

État au 12 octobre 2026. Trois chantiers : le design (fait), la base de
données et la collecte des événements (à consolider), l'espace pour que les
bars publient eux-mêmes (à construire).

Ce document distingue ce qui est **vérifié** (lu dans le code ou dans la
documentation de l'hébergeur) de ce qui est une **hypothèse** à confirmer.

---

## 1. Où on en est

| Chantier | État | Constat (vérifié dans le code) |
|---|---|---|
| Design | Fait | Accueil refondu, système décrit dans `DESIGN.md`. |
| Base de données | Fragile | Une seule table `events`, pas de notion de lieu, d'origine ni de statut. Rien n'est jamais supprimé. |
| Collecte | Large mais non mesurée | 29 adresses dans `config.py`, une méthode générique pour toutes. Rendement réel inconnu (voir étape 0). |
| Espace lieux | Inexistant | Aucun compte, aucun formulaire. Aucun bar dans les sources. |

### Les faiblesses précises de la base actuelle

1. **Identifiant fragile.** Un événement est identifié par `titre + date`.
   Conséquences : deux « Soirée DJ » le même soir dans deux bars n'en font
   qu'une (la seconde écrase la première) ; si une source corrige une
   virgule dans le titre, l'événement apparaît en double.
2. **Pas de lieu.** Le lieu est un texte libre, parfois réduit à
   « Lausanne ». Impossible de rattacher un événement à un bar, donc
   impossible de donner à un bar l'accès à « ses » événements.
3. **Pas d'origine ni de source exacte.** Tous les événements collectés
   portent l'étiquette `scraper`. On ne sait pas quel site a produit quelle
   fiche, ni distinguer un événement saisi par un bar d'un événement collecté.
4. **Pas de statut.** Pas de « en attente », « annulé », « masqué ». Un
   événement annulé par la salle reste affiché.
5. **Pas de doublons gérés entre sources.** Le même concert vu sur l'agenda
   de la Ville et sur le site de la salle donne deux fiches si les titres
   diffèrent légèrement.
6. **Pas de migrations.** Le schéma ne peut évoluer qu'en effaçant la base.

### Le point bloquant : l'hébergement actuel efface la base

**Vérifié** (documentation Render) : en offre gratuite, le disque est
éphémère. Le fichier `events.db` est effacé à chaque redéploiement **et** à
chaque mise en veille (après 15 minutes sans visite). Le réveil prend environ
une minute.

- Aujourd'hui, c'est sans gravité : les événements collectés se recollectent.
- Demain, un événement saisi par un bar serait **perdu**. Le chantier 3 est
  impossible sans régler ça.
- Le réveil d'une minute contredit le principe « décider vite » de
  `PRODUCT.md`.

### Décision du 12 octobre 2026 : rester gratuit

L'option payante (Render Starter avec disque, ~USD 7.25/mois) a été écartée.
La base quitte Render et chaque service fait une seule chose :

| Rôle | Service | Offre gratuite (lue en octobre 2026, à revérifier) |
|---|---|---|
| Afficher le site | Render (inchangé) | 750 heures par mois ; veille après 15 min sans visite, réveil ~1 min. |
| Garder les événements et les lieux | Neon (base PostgreSQL) | 0,5 Go par projet, quota de calcul de 100 « CU-heures » par mois ; le calcul s'arrête après 5 min sans requête et redémarre à la suivante. |
| Collecter les événements | GitHub Actions | Gratuit pour un dépôt public. |

**Pourquoi Neon plutôt que Supabase :** Supabase met en pause un projet
gratuit après une semaine d'inactivité, et il reste hors ligne jusqu'à une
réactivation manuelle. Neon n'arrête que le calcul, qui redémarre seul.

**Pourquoi la collecte sur GitHub Actions :** aujourd'hui, elle ne tourne
que si quelqu'un visite le site. Sur GitHub, elle tourne à heures fixes, ne
dépend pas du réveil du site, et chaque passage laisse un journal lisible.

**Ce qu'on accepte avec le gratuit :**

- Le premier visiteur après 15 minutes de calme attend toujours environ une
  minute. Parade possible : un service gratuit qui visite le site toutes les
  10 minutes (un seul service allumé en continu consomme ~744 h, sous les
  750 h). **À vérifier** que Render le tolère.
- 0,5 Go suffit largement pour du texte, pas pour des photos. Les images
  envoyées par les bars (étape 3) iront chez un service d'images gratuit, à
  choisir le moment venu.
- Le quota de calcul de Neon impose que le site garde le programme en
  mémoire quelques minutes au lieu d'interroger la base à chaque visite.
- GitHub suspend les tâches planifiées d'un dépôt public après 60 jours sans
  activité ; un commit suffit à les relancer.
- Le dépôt est public : l'adresse secrète de la base ne doit **jamais** être
  écrite dans le code. Elle se range dans les « secrets » de GitHub et dans
  les variables d'environnement de Render.

---

## 2. Ordre proposé

1. **Étape 0 — Mesurer** (quelques jours)
2. **Étape 1 — Socle de données** (prérequis des deux suivantes)
3. **Étape 2 — Collecte fiable**
4. **Ouverture publique** (retrait du mot de passe)
5. **Étape 3 — Espace lieux**

En parallèle, dès maintenant : la **piste terrain** avec les bars (sans code).

**Pourquoi le socle avant tout le reste :** la collecte et l'espace lieux
écrivent tous deux dans la base. Si la base ne connaît ni « lieu », ni
« origine », ni « statut », on construirait les chantiers 2 et 3 deux fois.

**Pourquoi ouvrir au public avant l'espace lieux :** un bar publie là où il
y a du public. La collecte suffit pour lancer ; l'espace lieux est un levier
de croissance, pas un prérequis.

Chaque étape = une branche = une pull request, avec un critère « c'est fini
quand… ».

---

## Étape 0 — Mesurer avant de construire

1. Lancer l'audit des sources (`tools/audit_sources.py`). Il tourne sur
   GitHub Actions (onglet **Actions** > **Audit des sources** > **Run
   workflow**) et affiche un tableau sur la page du run : pour chaque
   source, répond-elle, combien d'événements à venir, avec quelle part
   d'heures, de lieux, d'images et de prix.
2. Classer les sources : **garder** (fonctionne), **réparer** (répond mais
   0 événement ou fiches incomplètes), **abandonner** (bloque ou interdit la
   collecte).
3. ~~Choisir l'hébergement~~ : fait, option gratuite (voir plus haut).

**Fini quand :** le tableau des sources est rempli.

---

## Étape 1 — Socle de données

### Mise en place de la base Neon

1. Vincent crée un compte Neon et un projet (région Europe).
2. Il range l'adresse de connexion dans les secrets de GitHub et dans les
   variables d'environnement de Render, sans jamais la coller dans le code
   ni dans une conversation.
3. Une seconde base « essai » (Neon appelle ça une branche) sert aux tests,
   pour ne jamais toucher à la vraie.
4. `db.py` est réécrit pour PostgreSQL ; le reste de l'application ne
   change pas.

### Ce qui change dans les données

**Nouvelle table `lieux`**

| Champ | Contenu |
|---|---|
| nom | nom du lieu |
| adresse, quartier | adresse postale, quartier (Flon, Centre, Sous-Gare…) |
| type | bar, club, salle de concert, théâtre, musée, cinéma |
| site web, page agenda | adresse collectée par le scraper, s'il y en a une |
| thème par défaut | Clubbing pour un club (aide le classement) |
| contact | nom, e-mail, téléphone (pour l'étape 3) |
| clé d'accès | lien secret pour l'espace lieux (étape 3) |
| confiance | publication directe ou validation requise |

**Table `events` enrichie**

| Champ ajouté | Rôle |
|---|---|
| lieu | lien vers la table `lieux` |
| origine | `collecte`, `lieu` (saisi par le bar) ou `admin` |
| source exacte | l'adresse de la page d'où vient la fiche |
| statut | `publié`, `en attente`, `annulé`, `masqué` |
| vu pour la première / dernière fois | pour détecter les disparitions |
| récurrence | « chaque mardi » (étape 3) |

### Les règles

- **Identifiant stable :** l'adresse de la page de l'événement quand la
  source en donne une ; sinon lieu + date + heure + titre normalisé.
- **Doublons :** même lieu, même jour, titre proche → une seule fiche.
  Priorité : le lieu lui-même > le site du lieu > un agenda généraliste.
- **Disparition :** un événement futur absent de sa source deux collectes
  de suite est masqué (probablement annulé), pas supprimé.
- **Archivage :** les événements passés depuis plus de 30 jours sont
  archivés.
- **Migrations :** la base porte un numéro de version ; chaque évolution du
  schéma est un petit script appliqué au démarrage, sans perte de données.

**Fini quand :** les tests passent, les données existantes sont migrées, et
un redéploiement ne fait perdre aucun événement (test : compter avant et
après).

---

## Étape 2 — Collecte fiable

1. **Planifiée sur GitHub Actions, plus déclenchée par les visites.** Deux
   à quatre fois par jour, une seule collecte à la fois (aujourd'hui, les
   deux processus du serveur peuvent en lancer une chacun). Le site, lui, ne
   fait plus que lire la base.
2. **Protéger `/api/refresh`.** Aujourd'hui, n'importe qui derrière le mot de
   passe peut relancer une collecte par un simple lien. Une fois le mot de
   passe retiré, n'importe quel robot pourra le faire. Il faut une clé.
3. **Un module par source importante.** La méthode générique actuelle (JSON-LD
   puis devinette dans le HTML) reste pour les petites sources. Les sources
   prioritaires reçoivent chacune un petit module dédié, testé sur une copie
   enregistrée de leur page : si le site change, le test le signale.
   Priorité : concerts, clubs, bars (le public cible), puis selon le
   rendement mesuré à l'étape 0.
4. **Ajouter les bars.** Constituer la liste des 15 à 20 bars et petits lieux
   cibles. Pour chacun : a-t-il un agenda sur un site web ? Beaucoup ne
   publient que sur Instagram, ce qui ne se collecte pas (techniquement et
   selon les conditions de Meta). C'est précisément la raison d'être de
   l'étape 3.
5. **Qualité des fiches.** Thème déduit du type de lieu avant les mots-clés ;
   rattachement de chaque fiche à un lieu connu.
6. **Surveillance.** Une page d'administration des sources, et une alerte
   quand une source qui donnait des événements tombe à zéro.
7. **Mini-administration.** Masquer ou corriger un événement, marquer à la
   main « À ne pas manquer » (règle éditoriale aujourd'hui ouverte dans
   `PRODUCT.md`).

### Cadre légal et bonne conduite (hypothèses à faire valider)

- Respecter `robots.txt`, collecter lentement, toujours renvoyer vers la
  source, ne reprendre que des extraits courts.
- Les photos sont protégées par le droit d'auteur (LDA). Aujourd'hui le site
  affiche l'image hébergée chez la source sans la copier ; à garder ainsi.
- Reprendre systématiquement l'agenda compilé par un tiers (agrégateurs)
  pourrait tomber sous l'art. 5 let. c LCD (reprise d'un résultat de travail
  par des procédés techniques). Les conditions d'utilisation de certains
  sites (Resident Advisor notamment) interdisent probablement la collecte
  automatique. **À vérifier avant l'ouverture publique.**
- La voie la plus solide : les données des lieux eux-mêmes, idéalement avec
  leur accord, ce qui rejoint l'étape 3.

**Fini quand :** chaque source prioritaire a son module et son test, la
collecte tourne seule, la page des sources montre l'état de chacune.

---

## Étape 3 — Espace lieux

Principe : un gérant de bar publie sa soirée **depuis son téléphone, en
moins d'une minute, sans mot de passe**.

1. **Accès par lien personnel.** Chaque lieu reçoit un lien secret (généré
   dans l'administration, envoyé par WhatsApp ou e-mail), comme le lien de
   partage d'un document. Révocable à tout moment. Plus tard, avec beaucoup
   de lieux : connexion par lien reçu par e-mail.
2. **Formulaire mobile.** Titre, date, heure, prix ou gratuit, thème, image
   (photo du flyer), lien de billetterie, texte court.
3. **Récurrence.** « Chaque mardi » : quiz, jam, karaoké. Essentiel pour les
   bars.
4. **Dupliquer** une soirée passée en un geste.
5. **Modération.** Les nouveaux lieux passent par une validation ; les lieux
   de confiance publient directement.
6. **Fusion avec la collecte.** Si le bar publie un événement déjà collecté,
   sa version l'emporte.
7. **Page publique du lieu.** Tous ses événements à venir, sur une adresse
   que le bar peut mettre dans sa bio Instagram : il nous amène son public.
8. **Plus tard : « Envoie ton flyer ».** Le bar envoie une photo du flyer ou
   le lien de sa publication Instagram ; l'IA (Claude, lecture d'image)
   pré-remplit le formulaire ; le bar valide.

Données personnelles : les contacts des lieux sont des données personnelles
(nLPD). Collecter le minimum et publier une courte mention de
confidentialité.

**Fini quand :** trois bars pilotes publient eux-mêmes pendant quatre
semaines.

---

## Piste terrain (sans code, à démarrer maintenant)

1. Lister 15 à 20 bars et petits lieux cibles.
2. En rencontrer cinq : comment annoncent-ils leurs soirées aujourd'hui ?
   Qui s'en occupe ? Saisiraient-ils leurs soirées ailleurs, et à quelle
   condition ?
3. Test possible avant de coder l'étape 3 : un simple formulaire en ligne
   (Tally, Google Forms) dont les réponses sont saisies à la main. Si les
   bars ne le remplissent pas, le futur espace lieux ne sera pas utilisé
   non plus.

Le vrai risque de l'étape 3 n'est pas technique : c'est l'adoption par les
bars.

---

## Décisions à prendre, dans l'ordre

1. ~~Hébergement~~ : décidé le 12 octobre 2026, option gratuite
   (Render + Neon + GitHub Actions).
2. Liste des bars et petits lieux cibles.
3. Date d'ouverture publique (proposition : après l'étape 2).
4. Modération : validation systématique au début (proposition : oui).
