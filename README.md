# IHME — Atelier de projets

Application pédagogique React 19, Express 5, PostgreSQL. Node 24 sert React compilé et l’API `/api` sur **3000**. Aucune dépendance à Coolify. Aucun déploiement automatique.

## Fonctionnement

- Promotion : recherche, progression des six jalons, alertes de blocage, échéances et revues anciennes.
- Une fiche par étudiant : identifiant pédagogique, objectif, dépôt GitHub/GitLab et URL déployée.
- **Activité Git réelle** : lecture à la demande des commits de la branche par défaut, pagination, lien vers le commit et sélection du SHA pour la revue. Aucune exécution du code étudiant.
- Jalons : statut, échéance et preuve/observation.
- Journal des revues : date, SHA examiné, acquis, blocage, prochaine étape, aide apportée. Les revues sont conservées ; la plus récente indique le blocage actuel.
- Grille facultative sur 20, partiellement remplissable. Aucun calcul de note à partir du nombre de commits.
- Connexion enseignant obligatoire pour **toutes** les données de suivi et les requêtes Git.

## Démarrer localement avec Docker

```sh
cp .env.example .env
docker compose up --build -d
docker compose run --rm app node server/seed.js
```

Ouvrir http://localhost:3000. Mot de passe **de démonstration uniquement** : `Demonstration-IHME-2026!`. Le seed ajoute quatre projets entièrement fictifs seulement si la base est vide. Il ne s’exécute jamais automatiquement en production.

```sh
docker compose logs app
docker compose down
```

Le volume `postgres-data` conserve les données après arrêt. Ne pas utiliser `down -v` sur une base à conserver.

## Développement React avec rechargement

Node 24 et npm sont nécessaires. Le PostgreSQL local est fourni par Compose sur localhost:55432 (port configurable par `POSTGRES_PORT`).

```sh
npm ci
cp .env.example .env
docker compose up -d db
node --env-file=.env server/migrate.js
node --env-file=.env server/seed.js
npm run dev:api
# Dans un second terminal
npm run dev
```

Ouvrir http://localhost:5173 et définir `PUBLIC_ORIGIN=http://localhost:5173` dans `.env` avant de lancer l’API. Vite relaie `/api` vers Node. En production, Vite n’est pas lancé.

Pour une démo sans Docker : `npm ci && npm run build && npm run demo:local`. Cette variante utilise PostgreSQL embarqué PGlite dans `.demo-data/`, exclusivement sur localhost. Le chemin normal de production utilise `pg` et PostgreSQL séparé.

## Relier les vrais dépôts étudiants

1. Se connecter comme enseignant et créer une fiche avec un identifiant pédagogique.
2. Renseigner l’URL racine HTTPS du dépôt : `https://github.com/organisation/projet` ou `https://gitlab.com/groupe/projet` (sous-groupes acceptés).
3. Sur la promotion, **Actualiser les dépôts Git** relève le dernier commit et sa date pour chaque dépôt (une fois par minute au maximum). Les échecs sont signalés et la date de vérification reste visible. Dans **Activité Git**, cliquer **Lire le dépôt Git**. La lecture ne copie pas les dépôts dans ce repository et ne conserve pas les réponses Git en base.
4. Cliquer **Examiner en revue** sur un commit : son SHA complet préremplit la nouvelle revue. Consulter son diff sur GitHub/GitLab, puis saisir l’observation pédagogique.

Les dépôts publics fonctionnent sans jeton, dans la limite des quotas du fournisseur. Pour les dépôts privés : configurer `GITHUB_TOKEN` (jeton finement limité aux seuls dépôts nécessaires, Contents en lecture) ou `GITLAB_TOKEN` (read_api, accès restreint) dans le fichier d’environnement **non versionné** du serveur. Les jetons restent côté Node, sont distincts des identifiants utilisés pour pousser cette application, et ne sont jamais intégrés au build React. L’application n’effectue aucune modification sur les dépôts étudiants.

La liste réelle des dépôts doit être fournie par l’enseignant. Aucun étudiant réel n’est préchargé dans la distribution publique. Les commits affichés concernent le dépôt et peuvent inclure le travail de plusieurs contributeurs : ils ne prouvent pas à eux seuls l’auteur ou la compréhension du travail. Les branches autres que celle par défaut se consultent directement dans la forge ; un SHA peut aussi être saisi manuellement dans la revue. Les instances GitLab auto-hébergées ne sont pas prises en charge.

## Vérifications

```sh
npm test
npm run build
docker build -t ihme-suivi:local .
```

Tests HTTP Supertest sur PostgreSQL embarqué : accès refusé sans connexion, origine des mutations, cookie, révocation de session, création des six jalons, revue/SHA, évaluation et persistance. Tests métier : dates, bornes des notes, alertes et seed non destructif. Tests d’intégration Git avec réponses simulées : URL autorisées, pagination, minimisation des données, quota et dépôt privé. La CI exécute tests, build React et build Docker ; elle ne déploie rien.

## Protection des données

Le dépôt public ne contient que du code et des exemples fictifs. `.env*` réels, sauvegardes, données locales et exports sont ignorés par Git et Docker. Utiliser des identifiants pédagogiques ; conserver toute correspondance nominative hors de ce dépôt. Ne jamais copier observations ou liens privés dans une issue publique.

Sessions : jeton aléatoire 256 bits, seul son SHA-256 est stocké en PostgreSQL, expiration à 8 h, cookie HttpOnly/SameSite Strict et Secure en production, invalidation côté serveur à la déconnexion. Vérification stricte de `Origin` sur les mutations, limitation des essais de connexion, requêtes SQL paramétrées, réponses sans cache, en-têtes Helmet. Pas de stockage du mot de passe dans la base : il provient de l’environnement serveur. Changer le mot de passe ne révoque pas les sessions existantes : exécuter `DELETE FROM sessions` via l’administrateur de la base pour les invalider.

Une seule identité enseignante est prévue pour ce cours ; pas de comptes étudiants ni de gestion multi-enseignants. Le reverse proxy HTTPS et l’accès administratif au serveur font partie de l’exploitation. Définir une durée de conservation des observations et des sauvegardes adaptée au cours ; effectuer les suppressions administrativement sur la base, jamais dans Git. Le endpoint public `/api/health` ne divulgue aucune fiche.

## Déploiement

Voir [le guide Infomaniak et son scénario de démonstration](docs/deploiement.md). Configuration pour un **serveur Infomaniak administré disposant de Docker Engine et Compose**, avec PostgreSQL partagé déjà présent. Les noms du conteneur PostgreSQL, des réseaux et du reverse proxy sont à adapter à l’infrastructure existante ; aucune hypothèse d’accès au serveur n’a été vérifiée et aucune commande distante n’a été exécutée.

### Importer une promotion réelle en privé

Préparer hors du dépôt public un tableau JSON contenant uniquement les champs `student_name`, `title`, `repository_url` et éventuellement `objective` / `deployed_url`. Exemple fictif :

```json
[{"student_name":"Étudiant démo","title":"Projet de démonstration","repository_url":"https://github.com/exemple/projet"}]
```

Le répertoire local `.private/` est ignoré par Git **et** Docker. Sur une base vide migrée, importer via stdin :

```sh
docker compose exec -T app node server/import-roster.js < .private/roster.json
```

L’import est transactionnel, ajoute les six jalons et ignore les dépôts déjà présents sans écraser les observations. Il ne crée aucune revue et n’invente aucune évaluation à partir des mails. Les noms, liens et observations réels restent dans PostgreSQL et les fichiers privés locaux ; ne jamais utiliser `git add -f` pour ces fichiers. Pour la démonstration fictive et le suivi réel, utiliser des bases/volumes distincts.
