# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Habitants de Lausanne, en priorité les jeunes (tranche d'âge exacte non fixée). Ils cherchent quoi faire ce soir ou ce week-end et veulent trouver vite une sortie, y compris dans des lieux qu'ils ne connaissent pas encore.

« Jeune » renvoie d'abord à un usage pratique, pas à un style : un visuel clair, des événements qui les concernent, un outil qui va droit au but.

Le site est pensé d'abord pour le mobile (selon le README ; usage mobile majoritaire non mesuré).

## Product Purpose

Rassembler en un seul endroit toute la vie culturelle et nocturne de Lausanne, des grandes institutions jusqu'aux bars et petits lieux, pour aider à **décider vite** et à **découvrir**.

Succès, dans l'ordre :
1. Devenir la référence de l'agenda culturel lausannois pour les jeunes.
2. Ensuite, éventuellement, monétiser : publicité ou petit abonnement (ordre de grandeur évoqué : CHF 5 par an). Modèle non décidé.

## Positioning

L'agenda officiel de la Ville (agenda.lausanne.ch) a un registre très classique et n'affiche pas les événements des bars et des petits lieux. Lausanne Cultura s'adresse aux jeunes et combine les agendas officiels avec les programmes des salles indépendantes, clubs et petits lieux, que personne ne réunit aujourd'hui en un seul endroit.

## Operating Context

- Les événements sont collectés automatiquement (scraping). Source principale : l'agenda de Lausanne Tourisme (environ 1 200 événements dans quelque 200 lieux, bars et petits lieux compris), complété par le calendrier de l'OCL. Liste dans `config.py` ; état de toutes les sources auditées dans `SOURCES.md`.
- La collecte se relance au plus une fois par heure, quand quelqu'un consulte le site ; elle peut aussi être forcée via `/api/refresh`.
- Chaque événement est classé automatiquement dans un thème : d'abord par son lieu quand celui-ci a un programme d'un seul genre (Cinémathèque, Docks, D! Club…), sinon par mots-clés. En cas de doute, il tombe dans « Culture ».
- La qualité des données collectées varie selon la source : prix souvent absent, horaire, image ou adresse parfois manquants, lieu parfois réduit à « Lausanne ». Lausanne Tourisme ne donne ni heure ni prix dans sa liste : jours, heure et prix sont lus sur la fiche de chaque événement, quelques-unes par collecte, les plus proches d'abord ; tant qu'une fiche n'est pas lue, l'événement s'affiche sur toute sa période, sans heure. L'interface doit fonctionner avec des fiches incomplètes.

## Capabilities and Constraints

- Fonctions actuelles : recherche par mot-clé, filtre par thème, sélection « À ne pas manquer », fiche détaillée avec lien vers le site officiel de l'événement.
- Thèmes : Musique, Théâtre, Exposition, Cinéma, Danse, Festival, Famille, Conférence, Sport, Humour, Atelier, Marché, Clubbing (+ « Culture » par défaut).
- Pas de compte utilisateur ni de billetterie.
- Prévu dans la refonte de l'accueil : partager un événement ; filtre « gratuit / petit prix » (limité tant que les prix collectés manquent souvent) ; **mes goûts** : choisir les thèmes et lieux qui intéressent, masquer ceux qui n'intéressent jamais (exemple : ne plus voir l'Opéra), enregistrés sur le téléphone, sans compte.
- Langue : français uniquement. Contexte suisse (prix en CHF).
- Hébergement : Render, offre gratuite. L'accès en ligne est pour l'instant protégé par mot de passe.
- Décisions ouvertes :
  - **Bars et petits lieux** : objectif central. Lausanne Tourisme en apporte quelques-uns (Jumeaux Jazz Club, Base Bar, Satellite, Barberousse) ; la couverture reste partielle, et Resident Advisor et Shotgun, riches en soirées, bloquent les robots.
  - Tranche d'âge exacte du public cible.
  - Modèle de monétisation (publicité ou abonnement) et calendrier.
  - Date d'ouverture publique (retrait du mot de passe).
  - La mise en avant « À ne pas manquer » repose sur un marqueur que les événements collectés ne reçoivent jamais ; faute de marqueur, le site affiche les premiers événements avec image. Règle de sélection éditoriale à définir.

## Brand Commitments

- Nom : **Lausanne Cultura**.
- Présents dans le code mais pas confirmés comme définitifs : le monogramme « L·C » et l'accroche « Vivez la culture, une nuit à la fois. »
- Registre voulu : direct et pratique, à l'opposé du ton institutionnel et classique de l'agenda officiel.

## Evidence on Hand

- `seed_data.py` : 25 événements de **démonstration fictifs** (photos de banque d'images Unsplash, liens vides `#`). Ils servent seulement quand la collecte ne renvoie rien. Ne jamais les présenter comme de vrais événements.
- Le pied de page crédite agenda.lausanne.ch comme source de données.
- Absents du dépôt, à ne pas inventer : chiffres d'audience, témoignages d'utilisateurs, partenariats avec des lieux, articles de presse, nombre d'abonnés ou tarifs définitifs.

## Product Principles

1. **Décider vite.** La question « que faire ce soir ou ce week-end ? » doit trouver une réponse en quelques secondes.
2. **Faire découvrir.** Les petits lieux et les scènes alternatives ont autant de place que les grandes institutions.
3. **Droit au but.** Un visuel clair et pratique : chaque élément aide à choisir, rien ne retarde la décision. Ton direct, loin du registre institutionnel.
4. **Honnêteté des données.** Afficher ce qui est connu, signaler clairement ce qui manque, ne jamais combler un trou par une information inventée.
5. **Chacun son fil.** Chacun voit d'abord ce qui l'intéresse ; ce qui est masqué reste signalé et récupérable d'un geste.
