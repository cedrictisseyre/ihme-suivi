// Référentiel formatif : M2 IHME STAPS, initiation de 10 heures.
export const RUBRIC_VERSION = "ihme-staps-10h-v1";
export const RUBRIC = [
  {
    position: 1,
    title: "Cadrage du besoin",
    expected: "Décrire un utilisateur STAPS, un besoin et un scénario simple.",
    demonstration:
      "Expliquer en une minute qui utilise l’outil et ce qu’il permet de faire.",
    next: "Compléter le README : utilisateur, problème, entrée et résultat attendu.",
  },
  {
    position: 2,
    title: "Modèle de données",
    expected:
      "Identifier les données utiles, leurs types, une clé primaire et, si nécessaire, une relation. Montrer une requête SQL.",
    demonstration:
      "Présenter une table et expliquer une requête SELECT ou INSERT sur un jeu d’exemples.",
    next: "Écrire un petit schéma SQL et un jeu d’exemples, puis expliquer les clés et les unités.",
  },
  {
    position: 3,
    title: "API et règles métier",
    expected:
      "Transformer des entrées en un résultat utile : moyenne, filtre, classement ou autre calcul adapté au projet. Contrôler les entrées.",
    demonstration:
      "Suivre un exemple à la main, puis retrouver le même résultat dans l’application.",
    next: "Isoler un calcul ou une règle et vérifier les cas normal, vide et limite.",
  },
  {
    position: 4,
    title: "Interface React",
    expected:
      "Permettre une saisie ou une sélection et afficher un résultat lisible avec intitulés, unités et retour d’erreur.",
    demonstration: "Faire réaliser le scénario principal à une autre personne.",
    next: "Relier un formulaire ou une sélection au résultat et ajouter un message compréhensible en cas d’erreur.",
  },
  {
    position: 5,
    title: "Intégration et tests",
    expected:
      "Démontrer un parcours de bout en bout et documenter trois essais : normal, vide et limite. Vérifier la persistance si le projet en utilise.",
    demonstration:
      "Rejouer les trois essais et expliquer un écart corrigé. Un tableau de tests manuels est accepté.",
    next: "Consigner trois essais avec entrée, résultat attendu et résultat obtenu.",
  },
  {
    position: 6,
    title: "Déploiement et documentation",
    expected:
      "Fournir un lien ou une procédure reproductible, expliquer un morceau de code et indiquer une limite et une amélioration.",
    demonstration:
      "Ouvrir le projet, expliquer son calcul et sa circulation des données, puis nommer une limite.",
    next: "Vérifier le lien, compléter les instructions et préparer une explication personnelle de deux minutes.",
  },
];
export const ASSESSMENT_GUIDE = [
  {
    key: "functionality",
    title: "Scénario utile et fonctionnement",
    max: 6,
    anchors:
      "0 : aucun scénario démontré ; 2 : éléments isolés ; 4 : parcours principal utilisable avec aide ; 6 : parcours cohérent, entrées et résultat contrôlés.",
  },
  {
    key: "design",
    title: "Algorithme et modèle de données",
    max: 4,
    anchors:
      "0 : non expliqué ; 1 : données repérées ; 2 : modèle ou calcul cohérent ; 3 : les deux sont reliés ; 4 : choix, clés, unités et cas limite expliqués.",
  },
  {
    key: "quality",
    title: "Lisibilité et vérifications",
    max: 3,
    anchors:
      "0 : aucune vérification montrée ; 1 : code repérable et essai normal ; 2 : trois essais documentés ; 3 : contrôles des entrées et correction expliquée.",
  },
  {
    key: "progression",
    title: "Démarche et progression",
    max: 3,
    anchors:
      "0 : démarche non documentée ; 1 : une étape explicitée ; 2 : problème et modification retracés ; 3 : démarche expliquée et prochaine étape pertinente. Le nombre de commits ne détermine pas la note.",
  },
  {
    key: "explanation",
    title: "Compréhension et recul",
    max: 4,
    anchors:
      "0 : non expliqué ; 1 : décrit l’interface ; 2 : explique un calcul ; 3 : suit les données jusqu’au résultat ; 4 : justifie un choix et une limite. À apprécier en échange, sans déduction automatique.",
  },
];
