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
| Collecte | En panne | Aucune des 29 sources de `config.py` ne donne d'événement à venir (audit, section 2). |
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
  envoyées par les bars (étape 4) iront chez un service d'images gratuit, à
  choisir le moment venu.
- Le quota de calcul de Neon impose que le site garde le programme en
  mémoire quelques minutes au lieu d'interroger la base à chaque visite.
- GitHub suspend les tâches planifiées d'un dépôt public après 60 jours sans
  activité ; un commit suffit à les relancer.
- Le dépôt est public : l'adresse secrète de la base ne doit **jamais** être
  écrite dans le code. Elle se range dans les « secrets » de GitHub et dans
  les variables d'environnement de Render.

---

## 2. Résultat de l'étape 0 : la collecte ne ramène rien

Audit lancé le 12 octobre 2026 depuis GitHub Actions
(`tools/audit_sources.py`). **Aucune des 29 sources ne donne un seul
événement à venir.**

| Ce qui se passe | Sources | Nb | Que faire |
|---|---|---:|---|
| La page n'existe pas (erreur 404) | lausanne.ch (page agenda), vidy.ch, lesdocks.ch, chorus.ch, dclub.ch, cinematheque.ch, zinema.ch | 7 | Trouver la vraie page agenda. |
| Le domaine n'existe pas | agenda.lausanne.ch, casinodemontbenon.ch, folklore-club.ch | 3 | Vérifier si le lieu existe encore et sous quelle adresse. |
| Le site refuse les robots (403, 429) | ra.co, shotgun.live, leromandie.ch, fondation-hermitage.ch | 4 | Ne pas forcer. Demander au lieu, ou passer par l'espace lieux. |
| Certificat de sécurité refusé | le-bourg.ch | 1 | À examiner. |
| Répond, mais aucun événement reconnu | lausanne-tourisme.ch (40 pages suivies, aucune lisible), guidle.com, plateforme10.ch, tkm.ch, theatredebeaulieu.ch, opera-lausanne.ch, mcba.ch, elysee.ch, mudac.ch, cinemabellevaux.ch | 10 | Un module dédié par source. |
| Trouve les titres, mais pas les dates | mad.ch (80), ocl.ch (50), theatre-octogone.ch (20), arsenic.ch (1) | 4 | Un module dédié qui lit la date. Les réparations les plus rapides. |

Ce que ça veut dire :

- **Dix adresses sur 29 n'existent pas.** La liste de `config.py` n'a pas
  été vérifiée quand elle a été écrite.
- **Bonne nouvelle pour quatre sources :** les titres trouvés sont de vrais
  événements (MAD : « Gameboy the mad gay party », « JETLAG » ; Octogone :
  « La Machine de Turing », « Land of Hope » ; Arsenic : « Grand
  Magasin »). Il ne manque que la date. Chez OCL, une partie des titres
  sont des liens du menu (« Opéra de Lausanne ») mélangés aux concerts.
- **La méthode générique ne suffit pas.** Les sites qui répondent ne
  publient pas leurs événements dans un format standard lisible ; chacun
  demande un petit module sur mesure.
- **Conséquence probable en ligne (à vérifier en ouvrant le site) :** rien
  ce soir ni ce week-end ; seulement les ~150 fiches sans date de MAD, OCL,
  Octogone et Arsenic, rangées dans « Plus tard ».
- Réserve : l'audit tourne depuis les serveurs de GitHub. Render est aussi
  un centre de données, le résultat devrait être proche, mais `/api/sources`
  sur le site en ligne le confirmera.

Pour relancer l'audit : onglet **Actions** du dépôt > **Audit des sources**
> **Run workflow**. Le tableau s'affiche sur la page du run. Il se relance
aussi seul quand `config.py` ou `scraper.py` change.

---

## 3. Ordre proposé (revu après l'audit)

1. **Étape 0 — Mesurer** : fait.
2. **Étape 1 — Remettre de vrais événements** : priorité absolue, le site
   est vide sans ça.
3. **Étape 2 — Socle de données** (Neon, lieux, origine, statut).
4. **Étape 3 — Collecte planifiée et surveillée.**
5. **Ouverture publique** (retrait du mot de passe).
6. **Étape 4 — Espace lieux.**

En parallèle, dès maintenant : la **piste terrain** avec les bars (sans code).

**Pourquoi remettre des événements avant le socle :** les modules de
collecte produisent des fiches ; la façon de les enregistrer changera à
l'étape 2 sans qu'il faille les réécrire. Et ils fonctionnent dès
maintenant sur l'hébergement actuel : les événements sont simplement
recollectés après chaque réveil du site.

**Pourquoi le socle avant la collecte planifiée et l'espace lieux :** les
deux écrivent dans la base. Si la base ne connaît ni « lieu », ni
« origine », ni « statut », on les construirait deux fois.

**Pourquoi ouvrir au public avant l'espace lieux :** un bar publie là où il
y a du public. La collecte suffit pour lancer ; l'espace lieux est un levier
de croissance, pas un prérequis.

Chaque étape = une branche = une pull request, avec un critère « c'est fini
quand… ».

---

## Étape 1 — Remettre de vrais événements

1. **Ne plus enregistrer de fiche sans date.** Une fiche sans date n'aide
   pas à choisir une sortie (principe « honnêteté des données »).
2. **Corriger les dix adresses** qui n'existent pas : trouver la vraie page
   agenda de chaque lieu, retirer ceux qui ont fermé.
3. **Un module dédié pour 5 à 8 sources prioritaires**, chacun testé sur une
   copie enregistrée de la page : si le site change, le test le signale.
   Proposition de première vague :
   - MAD, Octogone, Arsenic : les titres sont déjà trouvés, il ne manque
     que la date. Réparations les plus rapides, et MAD vise le public cible.
   - Lausanne Tourisme et Guidle : agendas larges, qui couvrent aussi des
     bars.
   - Puis Les Docks, D! Club et Vidy, une fois leurs adresses corrigées.
4. **Les quatre sites qui bloquent les robots :** ne pas contourner leurs
   protections (risque juridique, et c'est mal vu des lieux qu'on veut
   ensuite convaincre). Les mettre sur la liste de la piste terrain.
5. L'audit sert de contrôle : chaque pull request qui touche la collecte le
   relance.

**Fini quand :** l'audit montre au moins 50 événements réels à venir sur
les sept prochains jours (seuil proposé, à ajuster), et plus aucune fiche
sans date.

---

## Étape 2 — Socle de données

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
| contact | nom, e-mail, téléphone (pour l'étape 4) |
| clé d'accès | lien secret pour l'espace lieux (étape 4) |
| confiance | publication directe ou validation requise |

**Table `events` enrichie**

| Champ ajouté | Rôle |
|---|---|
| lieu | lien vers la table `lieux` |
| origine | `collecte`, `lieu` (saisi par le bar) ou `admin` |
| source exacte | l'adresse de la page d'où vient la fiche |
| statut | `publié`, `en attente`, `annulé`, `masqué` |
| vu pour la première / dernière fois | pour détecter les disparitions |
| récurrence | « chaque mardi » (étape 4) |

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

## Étape 3 — Collecte planifiée et surveillée

1. **Planifiée sur GitHub Actions, plus déclenchée par les visites.** Deux
   à quatre fois par jour, une seule collecte à la fois (aujourd'hui, les
   deux processus du serveur peuvent en lancer une chacun). Le site, lui, ne
   fait plus que lire la base.
2. **Protéger `/api/refresh`.** Aujourd'hui, n'importe qui derrière le mot de
   passe peut relancer une collecte par un simple lien. Une fois le mot de
   passe retiré, n'importe quel robot pourra le faire. Il faut une clé.
3. **Étendre les modules dédiés** (commencés à l'étape 1) aux autres
   sources qui répondent. La méthode générique reste pour les petites
   sources. Priorité : concerts, clubs, bars (le public cible).
4. **Ajouter les bars.** Constituer la liste des 15 à 20 bars et petits lieux
   cibles. Pour chacun : a-t-il un agenda sur un site web ? Beaucoup ne
   publient que sur Instagram, ce qui ne se collecte pas (techniquement et
   selon les conditions de Meta). C'est précisément la raison d'être de
   l'étape 4.
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
  leur accord, ce qui rejoint l'étape 4.

**Fini quand :** la collecte tourne seule à heures fixes, chaque source
active a son module et son test, et une source qui tombe à zéro déclenche
une alerte.

---

## Étape 4 — Espace lieux

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
3. Test possible avant de coder l'étape 4 : un simple formulaire en ligne
   (Tally, Google Forms) dont les réponses sont saisies à la main. Si les
   bars ne le remplissent pas, le futur espace lieux ne sera pas utilisé
   non plus.

Le vrai risque de l'étape 4 n'est pas technique : c'est l'adoption par les
bars.

---

## Décisions à prendre, dans l'ordre

1. ~~Hébergement~~ : décidé le 12 octobre 2026, option gratuite
   (Render + Neon + GitHub Actions).
2. Liste des bars et petits lieux cibles.
3. Date d'ouverture publique (proposition : après l'étape 3).
4. Modération : validation systématique au début (proposition : oui).
