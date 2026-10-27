# Progression — M2 IHME STAPS, programmation, algorithmique et bases de données

Référentiel formatif pour un module de **10 heures**, dont **2 heures restantes**. L’objectif est un petit scénario utile et compris, avec des données fictives, un traitement explicable et une démonstration reproductible. La richesse graphique, le nombre de fonctionnalités ou de commits ne mesurent pas l’apprentissage. Une fonctionnalité modeste maîtrisée est suffisante pour démontrer une compétence.

## Les six jalons

| Jalon | Attendu à l’issue des 10 h | Preuve à présenter |
|---|---|---|
| 1. Cadrage | Un utilisateur STAPS, un besoin précis, des entrées et un résultat. | README court et explication d’une minute. |
| 2. Données | Données utiles et types, clé primaire, relation si nécessaire, requête SQL. | Petit schéma, données fictives et explication d’un SELECT ou INSERT. |
| 3. Algorithme et API | Un calcul, filtre ou classement pertinent ; contrôle des entrées. | Exemple calculé à la main, résultat identique dans l’outil ; cas vide et limite. |
| 4. Interface | Saisie ou sélection, résultat lisible, unités et messages compréhensibles. | Un camarade réalise le scénario principal. |
| 5. Intégration et essais | Parcours complet et trois essais documentés : normal, vide, limite. Persistance vérifiée si utilisée. | Tableau entrée / attendu / obtenu ; tests manuels acceptés. |
| 6. Livraison et compréhension | Lien ou procédure reproductible, explication du code, une limite et une amélioration. | Démonstration de deux minutes et questions de l’enseignant. |

Exemple : saisir des durées fictives de séances, stocker ces séances, calculer une durée moyenne et afficher le résultat avec son unité. Vérifier un jeu normal, une liste vide et une valeur nulle ou négative. Il n’est pas demandé de construire un outil médical ni de manipuler des données de santé réelles.

## Lecture des résultats

- **À faire** : aucune validation enseignante ; l’absence d’indice automatique ne prouve pas l’absence de travail.
- **En cours** : indice repéré dans le dépôt ou statut choisi par l’enseignant.
- **Validé** : validation explicite par l’enseignant après démonstration.
- **Bloqué** : difficulté identifiée par l’enseignant.

Le bilan automatique lit un échantillon de fichiers d’un commit précis, sans exécuter le code étudiant. Il cherche des indices : README, SQL, traitement et routes, interface, essais et livraison. Un mot-clé ou un fichier n’est pas une preuve de fonctionnement, de maîtrise ni d’auteur du travail. Le bilan ne valide aucun jalon et n’attribue aucune note. Une erreur d’accès ou une lecture partielle est signalée ; le dernier bilan réussi reste disponible. Les corrections enseignantes ont priorité et ne sont pas écrasées.

## Évaluation facultative sur 20

Les cinq critères conservent les plafonds du carnet existant. Les points sont attribués par l’enseignant, en s’appuyant sur la démonstration et l’explication personnelle, y compris lorsque l’étudiant utilise une assistance au code.

| Critère | Points | Repères |
|---|---:|---|
| Scénario utile et fonctionnement | 6 | 0 : non démontré ; 2 : éléments isolés ; 4 : scénario utilisable avec aide ; 6 : parcours cohérent, entrées et résultat contrôlés. |
| Algorithme et modèle de données | 4 | 0 : non expliqué ; 1 : données repérées ; 2 : modèle ou calcul cohérent ; 3 : les deux reliés ; 4 : choix, clés, unités et limite expliqués. |
| Lisibilité et vérifications | 3 | 0 : aucune vérification montrée ; 1 : code repérable et essai normal ; 2 : trois essais documentés ; 3 : contrôles des entrées et correction expliquée. |
| Démarche et progression | 3 | 0 : non documentée ; 1 : une étape explicitée ; 2 : problème et correction retracés ; 3 : démarche et prochaine étape pertinentes. Aucun barème fondé sur le volume de commits. |
| Compréhension et recul | 4 | 0 : non expliqué ; 1 : décrit l’interface ; 2 : explique un calcul ; 3 : suit les données jusqu’au résultat ; 4 : justifie un choix et une limite. |

Une compétence non observée est à vérifier : elle ne reçoit pas automatiquement zéro. Une grille incomplète n’affiche pas de total.

## Proposition pour les deux dernières heures

| Temps | Activité |
|---|---|
| 0–10 min | Lire le bilan, choisir un scénario minimal et une priorité. |
| 10–40 min | Terminer le lien entre données, traitement et résultat. |
| 40–65 min | Vérifier le schéma et la persistance ; faire expliquer une requête et le calcul. |
| 65–85 min | Rejouer les trois essais, corriger le problème principal. |
| 85–110 min | Démonstrations entre pairs et passages courts de l’enseignant. |
| 110–120 min | Mettre à jour README, lien et bilan ; noter une limite et la prochaine étape. |

## Galerie et publication

Chaque projet dispose d’un lien **Progression** public, sans connexion. Il présente les attendus, les indices automatiques, les statuts des jalons et les retours explicitement publics. Le bilan n’est pas une note officielle et les projets ne sont pas classés.

Les observations privées déjà saisies ne sont pas exportées. Dans le carnet, le champ « Retour public » d’un jalon permet de guider l’étudiant. Une revue ou une évaluation devient publique avec son option de publication ; pour les revues, seuls les acquis et la prochaine étape sont publiés, pas les champs blocage ou accompagnement. Les anciens éléments restent privés par défaut. Seul l’enseignant connecté peut modifier les résultats.

L’analyse peut être déclenchée depuis une fiche ou pour la promotion. Elle est aussi exécutée après la synchronisation Git planifiée ; les analyses sont renouvelées toutes les quatre heures et la galerie est régénérée toutes les cinq minutes par les timers existants. L’analyse de promotion lancée dans le carnet s’exécute en arrière-plan ; suivre son résultat avant d’actualiser la galerie. Installer les scripts de galerie et la configuration Caddy mis à jour pour exposer `/progression/`.


## Lire l’évaluation automatique dans les deux espaces

La galerie et le carnet affichent un encadré **Évaluation automatique** sur chaque carte, avant la miniature. Il indique le nombre de jalons avec des indices dans le dépôt et ouvre le diagnostic détaillé : points repérés, état des six jalons et trois priorités au maximum. La fiche enseignante s’ouvre directement sur l’onglet **Évaluation automatique**. Le bouton **Actualiser les évaluations automatiques** relance la lecture de la promotion.

Le compteur « 4/6 jalons avec indices » décrit ce que le programme a repéré dans un échantillon ; ce n’est ni une note ni un pourcentage de compétences acquises. La validation enseignante et l’évaluation facultative sur 20 sont affichées séparément. Les bilans indisponibles sont indiqués « Évaluation en attente ».

Le pied de page décrit les données réelles de la promotion suivie. Les exemples ou jeux d’essai de la grille restent des supports pédagogiques.
