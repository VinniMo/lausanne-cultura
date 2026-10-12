# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Habitants de Lausanne, en priorité les jeunes (tranche d'âge exacte non fixée). Ils cherchent quoi faire ce soir ou ce week-end et veulent trouver vite une sortie, y compris dans des lieux qu'ils ne connaissent pas encore.

Le site est pensé d'abord pour le mobile (selon le README ; usage mobile majoritaire non mesuré).

## Product Purpose

Rassembler en un seul endroit toute la vie culturelle et nocturne de Lausanne, des grandes institutions jusqu'aux bars et petits lieux, pour aider à **décider vite** et à **découvrir**.

Succès, dans l'ordre :
1. Devenir la référence de l'agenda culturel lausannois pour les jeunes.
2. Ensuite, éventuellement, monétiser : publicité ou petit abonnement (ordre de grandeur évoqué : CHF 5 par an). Modèle non décidé.

## Positioning

L'agenda officiel de la Ville (agenda.lausanne.ch) a un registre très classique et n'affiche pas les événements des bars et des petits lieux. Lausanne Cultura s'adresse aux jeunes et combine les agendas officiels avec les programmes des salles indépendantes, clubs et petits lieux, que personne ne réunit aujourd'hui en un seul endroit.

## Operating Context

- Les événements sont collectés automatiquement (scraping) sur 27 sources : 5 agendas généralistes et 22 lieux (théâtres, salles de concert, clubs, musique classique, musées, cinémas). Liste dans `config.py`.
- La collecte se relance au plus une fois par heure, quand quelqu'un consulte le site ; elle peut aussi être forcée via `/api/refresh`.
- Chaque événement est classé automatiquement par mots-clés dans un thème. En cas de doute, il tombe dans « Culture ».
- La qualité des données collectées varie selon la source : prix souvent absent (« Voir détails »), horaire, image ou adresse parfois manquants, lieu parfois réduit à « Lausanne ». L'interface doit fonctionner avec des fiches incomplètes.

## Capabilities and Constraints

- Fonctions actuelles : recherche par mot-clé, filtre par thème, sélection « À ne pas manquer », fiche détaillée avec lien vers le site officiel de l'événement.
- Thèmes : Musique, Théâtre, Exposition, Cinéma, Danse, Festival, Famille, Conférence, Sport, Humour, Atelier, Marché, Clubbing (+ « Culture » par défaut).
- Pas de compte utilisateur, de favoris ni de billetterie.
- Langue : français uniquement. Contexte suisse (prix en CHF).
- Hébergement : Render, offre gratuite. L'accès en ligne est pour l'instant protégé par mot de passe.
- Décisions ouvertes :
  - **Bars et petits lieux** : objectif central, mais aucun bar ne figure encore dans les sources collectées.
  - Tranche d'âge exacte du public cible.
  - Modèle de monétisation (publicité ou abonnement) et calendrier.
  - Date d'ouverture publique (retrait du mot de passe).
  - La mise en avant « À ne pas manquer » repose sur un marqueur que les événements collectés ne reçoivent jamais ; faute de marqueur, le site affiche les premiers événements avec image. Règle de sélection éditoriale à définir.

## Brand Commitments

- Nom : **Lausanne Cultura**.
- Présents dans le code mais pas confirmés comme définitifs : le monogramme « L·C » et l'accroche « Vivez la culture, une nuit à la fois. »
- Registre voulu : parler aux jeunes, à l'opposé du ton institutionnel et classique de l'agenda officiel.

## Evidence on Hand

- `seed_data.py` : 25 événements de **démonstration fictifs** (photos de banque d'images Unsplash, liens vides `#`). Ils servent seulement quand la collecte ne renvoie rien. Ne jamais les présenter comme de vrais événements.
- Le pied de page crédite agenda.lausanne.ch comme source de données.
- Absents du dépôt, à ne pas inventer : chiffres d'audience, témoignages d'utilisateurs, partenariats avec des lieux, articles de presse, nombre d'abonnés ou tarifs définitifs.

## Product Principles

1. **Décider vite.** La question « que faire ce soir ou ce week-end ? » doit trouver une réponse en quelques secondes.
2. **Faire découvrir.** Les petits lieux et les scènes alternatives ont autant de place que les grandes institutions.
3. **Parler aux jeunes.** Ton direct et vivant, loin du registre institutionnel.
4. **Honnêteté des données.** Afficher ce qui est connu, signaler clairement ce qui manque, ne jamais combler un trou par une information inventée.
