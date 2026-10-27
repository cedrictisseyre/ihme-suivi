# Démonstration de déploiement — Infomaniak Docker Engine

Ce document décrit la procédure de déploiement et sa démonstration. Utiliser Docker Engine/Compose directement sur le nœud Jelastic, sans Coolify. Node expose un seul port interne 3000 pour React compilé et `/api`.

Le carnet et la galerie étudiante sont deux sites HTTPS distincts, sur le même hôte Docker. Leurs adresses et les mots de passe de production ne sont pas stockés dans le dépôt public. Les accès administrateur sont conservés séparément dans les fichiers privés d’exploitation.

## Architecture et prérequis

```text
Navigateur → HTTPS → reverse proxy existant → app:3000
                                              ↓ réseau Docker privé
                                      PostgreSQL partagé
                                      base/rôle ihme_suivi
```

Accès SSH d’administration, Docker Engine et plugin Compose, PostgreSQL partagé compatible (configuration locale testée sur PostgreSQL 17), DNS, certificats TLS et reverse proxy déjà administrés. Vérifier les noms réels des réseaux et l’alias DNS PostgreSQL avant l’intervention. Aucun port PostgreSQL ni 3000 ne doit être exposé publiquement dans la configuration serveur.

`compose.server.yaml` utilise des réseaux externes : `DB_NETWORK` pour la base, `PROXY_NETWORK` pour le proxy. Le service Node tourne sous l’utilisateur `node`, système de fichiers en lecture seule, sans capabilities Linux, avec rotation des logs et healthcheck HTTP incluant un accès à la base.

## 1. Préparer une image immuable hors serveur

Depuis un checkout validé, avec un registre auquel vous avez accès :

```sh
npm ci
npm test
npm run build
# Choisir une étiquette de version, idéalement le SHA du commit.
git rev-parse HEAD
# Remplacer SHA et adapter l’architecture au serveur (exemple amd64).
docker buildx build --platform linux/amd64 -t ghcr.io/cedrictisseyre/ihme-suivi:SHA --push .
```

Cette commande publie une image ; elle n’est pas exécutée automatiquement. Il est aussi possible de transférer une archive des seuls fichiers versionnés et de construire l’image directement sur le nœud cible. Exclure impérativement les fichiers privés et les données étudiantes du contexte de build. S’authentifier au registre via son mécanisme sécurisé, sans inscrire de jeton dans le dépôt ou dans l’historique du shell. Pour une distribution sans registre, utiliser `docker save` puis `docker load` sur l’hôte cible.

## 2. Créer le rôle et la base dédiés sur le PostgreSQL partagé

Faire exécuter `deploy/provision.sql` une seule fois par l’administrateur PostgreSQL, via psql interactif. `\password` demande le mot de passe sans l’inscrire dans le script. Ce fichier ne recrée pas le serveur partagé et ne supprime rien.

Le rôle `ihme_suivi` possède uniquement sa base et les objets de l’application. Il ne doit pas être superuser ni propriétaire d’autres bases. Pour une isolation effective dans un cluster partagé, l’administrateur doit également vérifier les droits CONNECT/PUBLIC des **autres bases** et les règles `pg_hba.conf`, qui peuvent autrement autoriser un nouveau rôle à s’y connecter. Ne pas modifier les autorisations des autres applications sans leur administrateur.

Le réseau Docker privé n’est pas une isolation SQL : les privilèges PostgreSQL restent indispensables. Le service applicatif n’utilise jamais le compte administrateur du cluster.

## 3. Installer uniquement la configuration d’exécution

Sur le serveur, dans un répertoire d’exploitation protégé, placer `compose.server.yaml` et copier `.env.server.example` vers `.env.server` :

```sh
chmod 600 .env.server
```

Renseigner :

- `APP_IMAGE` : image immuable préparée à l’étape 1.
- `DATABASE_URL` : rôle/base `ihme_suivi`, mot de passe dédié et alias du PostgreSQL partagé. Encoder les caractères spéciaux du mot de passe pour une URL.
- `ADMIN_PASSWORD` : mot de passe enseignant unique d’au moins 16 caractères, différent de la démo.
- `PUBLIC_ORIGIN` : origine HTTPS exacte, sans chemin ni barre finale.
- `COOKIE_SECURE=true`, `APP_VERSION=SHA`.
- `DB_NETWORK` et `PROXY_NETWORK` : noms réels des réseaux existants.
- Facultativement `GITHUB_TOKEN` / `GITLAB_TOKEN` : accès en lecture seule aux dépôts privés des étudiants.

Ne jamais faire de `COPY .env` dans une image. Ne pas afficher le rendu de `docker compose config` avec les secrets ; utiliser `--quiet`.

## 4. Reverse proxy HTTPS

Adapter `deploy/nginx.conf.example` au proxy existant : il relaie **tous** les chemins vers le port 3000 de l’application, y compris `/api`. Le proxy doit partager `PROXY_NETWORK` et résoudre le service applicatif ; si plusieurs stacks utilisent le nom `app`, définir un alias Docker unique et le reporter dans `proxy_pass`. Conserver les certificats dans l’infrastructure du proxy. Le DNS public pointe vers ce proxy.

Ne pas rendre le service directement accessible en HTTP public. L’application ne fait pas confiance aux en-têtes proxy pour calculer l’adresse IP : le quota est donc partagé derrière un proxy. Configurer aussi une limitation des essais de connexion au niveau du proxy si plusieurs enseignants utilisent l’instance.

## 5. Migration et lancement

```sh
docker compose --env-file .env.server -f compose.server.yaml config --quiet
docker compose --env-file .env.server -f compose.server.yaml pull
docker compose --env-file .env.server -f compose.server.yaml run --rm migrate
docker compose --env-file .env.server -f compose.server.yaml up -d
```

La migration initiale est additive, transactionnelle et idempotente ; un verrou PostgreSQL évite deux exécutions simultanées. Le service `app` attend également la réussite du service `migrate` au démarrage Compose. Ne jamais exécuter le seed sur une base destinée au suivi réel. Les futures évolutions non additives devront recevoir des migrations versionnées spécifiques.

## 6. Démonstration en 5 minutes

Pour montrer le déploiement sans toucher au serveur réel : lancer `docker compose up --build -d` localement, puis `docker compose run --rm app node server/seed.js`.

1. Montrer `docker compose ps` et http://localhost:3000/api/health : Node et PostgreSQL répondent.
2. Ouvrir la promotion sans session : la connexion enseignant est demandée. Une requête `/api/projects` renvoie 401.
3. Se connecter avec le mot de passe local de `.env.example`. Filtrer les blocages et ouvrir la fiche fictive.
4. Sur une fiche, saisir un dépôt de démonstration public autorisé. Lire son activité Git réelle et sélectionner un commit pour une revue. Saisir acquis, blocage et prochaine étape ; montrer le SHA complet conservé dans le journal.
5. Valider un jalon, renseigner sa preuve et ouvrir la grille facultative. Rafraîchir et vérifier la conservation des modifications.
6. Redémarrer `docker compose restart app` : les données et la session persistent en PostgreSQL.
7. Se déconnecter : l’ancien cookie ne permet plus d’accéder aux fiches.

Sur le serveur, après une intervention autorisée, effectuer les mêmes contrôles avec l’origine HTTPS réelle et des données de test isolées. Vérifier Secure/HttpOnly/SameSite dans le navigateur, la fermeture des ports publics et la persistance après redémarrage.

## Sauvegarde, restauration et retour arrière

L’administrateur peut sauvegarder **uniquement la base applicative**, via une connexion configurée hors du dépôt (par exemple service psql et `.pgpass` protégé). Exemples avec une variable `DATABASE_URL` chargée dans une session d’exploitation sécurisée :

```sh
pg_dump --dbname="$DATABASE_URL" --format=custom --file=ihme-suivi.dump
# Restaurer dans une base isolée préalablement créée, jamais directement sur la base utilisée.
pg_restore --dbname="$RESTORE_DATABASE_URL" --no-owner --no-acl ihme-suivi.dump
```

Chiffrer les sauvegardes, restreindre leur accès, fixer une rétention et tester périodiquement la restauration. Les dumps ne doivent jamais entrer dans le dépôt public. Sauvegarder avant migration. Un rollback applicatif consiste à remettre `APP_IMAGE` à la version précédente puis relancer Compose ; il ne restaure pas la base. Pour un changement SQL incompatible futur, préparer et tester une restauration avant la mise à jour.

Les sessions sont stockées en base : les révoquer après restauration d’un dump avec `DELETE FROM sessions`. Pour suspendre l’application sans toucher au PostgreSQL partagé : `docker compose --env-file .env.server -f compose.server.yaml stop app`.

## Sources techniques

- [Architecture Docker Engine](https://docs.docker.com/engine/)
- [Sécurité Express en production](https://expressjs.com/en/advanced/best-practice-security/)
- [API commits GitHub](https://docs.github.com/en/rest/commits/commits)
- [API commits GitLab](https://docs.gitlab.com/api/commits/)

La configuration est une stack Docker Engine standard à adapter au serveur Infomaniak existant ; elle ne dépend pas des offres Jelastic ou d’hébergement web mutualisé.

## Infrastructure et galerie étudiantes

Sur un Docker Engine neuf, `deploy/platform/compose.yaml` fournit PostgreSQL et Caddy. Créer les réseaux externes, copier `env.platform.example` en `.env.platform` privé, puis démarrer PostgreSQL, créer la base/rôle propres au carnet et appliquer la migration avant de lancer le proxy. Le mot de passe administrateur du cluster est différent de celui de la base IHME.

Le kit utilise `/opt/ihme-suivi` pour le code, `/opt/ihme-platform` pour les outils installés, `/etc/ihme-students` pour les configurations root des projets et `/var/backups/ihme` pour les sauvegardes locales. Le guide [hébergement étudiant](hebergement-etudiants.md) décrit les affectations privées, le provisionnement, les chemins React/Express et l’API HTTPS. Ne pas recréer la stack PostgreSQL sans son manifeste de réseaux étudiants généré.

Après installation, contrôler les deux certificats HTTPS, les 20 fiches privées, les 20 liens de galerie, les noms étudiants autorisés et l’absence d’adresses mail, jetons ou observations dans la page publique, le refus d’accès aux données sans session et le refus d’une mutation provenant du site étudiant. Tester le déploiement d’une application fictive puis son rollback avant de distribuer les accès. Les applications de test doivent être retirées à la fin de la recette.

Le timer `ihme-backup.timer` exécute la sauvegarde des bases chaque nuit vers 03 h 20 Europe/Paris ; sept versions locales sont conservées. Vérifier un premier dump et prévoir une copie chiffrée hors serveur. Aucune augmentation Jelastic ni distribution d’accès par mail n’est automatique.
