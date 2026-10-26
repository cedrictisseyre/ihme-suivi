# Déployer les projets étudiants sur le serveur du cours

Le carnet enseignant et les applications étudiantes utilisent le même Docker Engine, PostgreSQL partagé et un proxy HTTPS. Le carnet conserve une origine distincte des démonstrations étudiantes : des chemins différents sur un même hôte ne suffisent pas à protéger ses observations des scripts étudiants.

La galerie publique contient uniquement les titres et chemins des projets. Une page « application en attente » apparaît tant qu’un projet n’a pas été publié ou si son serveur est arrêté. Préparer les espaces ne publie pas automatiquement le code des dépôts étudiants.

## Accès étudiant par HTTPS

Chaque projet dispose d’un identifiant `pNN`, d’un dépôt d’images exact autorisé, d’un chemin web et d’un jeton personnel de déploiement. Les accès réels sont remis par l’enseignant dans un fichier **privé** `deploy.curl`, distinct pour chaque projet. Ne jamais versionner ce fichier, le copier dans une image, le mettre dans un questionnaire public ou le partager avec un autre projet.

Après construction et publication d’une image dans le dépôt attribué :

```sh
# Adapter le dépôt d’images et le chemin attribués. Le serveur utilise linux/amd64.
docker buildx build --platform linux/amd64 --build-arg BASE_PATH=/mon-projet/ \
  --tag ghcr.io/compte-exemple/projet-exemple:version --push .
# Remplacer la valeur par le digest SHA-256 de 64 caractères indiqué après le push.
curl --config deploy.curl --data '{"digest":"sha256:REMPLACER_PAR_64_CARACTERES"}'
```

Le jeton autorise uniquement la publication dans l’espace auquel il est affecté. Le serveur refuse les tags variables comme `latest`, les options Docker, les volumes déclarés par les images et les déploiements concurrents. Une tentative par minute est permise par projet. Si la nouvelle image ne devient pas saine, la version précédente est rétablie ; pour un premier déploiement défaillant, le conteneur est arrêté. Le rollback applicatif ne restaure pas les données SQL.

Pour un registre privé, l’administrateur configure un accès en lecture côté serveur. Un dépôt privé sans cet accès ne peut pas être téléchargé. Un jeton de registre global en écriture ne doit jamais être distribué à la promotion.

## Contrat d’une application

- React compilé et Express servent `0.0.0.0:3000`, avec l’API sous `/api`.
- L’application utilise `DATABASE_URL`, `PUBLIC_ORIGIN`, `BASE_PATH`, `PORT` et `NODE_ENV` fournis à l’exécution. `PUBLIC_ORIGIN` contient l’origine seule ; `BASE_PATH` contient le chemin attribué, par exemple `/mon-projet/`.
- Le conteneur démarre sous UID/GID 1000, avec un système de fichiers en lecture seule et `/tmp` temporaire. Aucun secret n’entre dans l’image.
- `GET /api/health` renvoie HTTP 200 lorsque l’application est prête, sans divulguer de secret ; vérifier aussi l’accès à sa propre base.
- Le pool PostgreSQL doit rester à **4 connexions maximum**. Les migrations ne concernent que la base propre au projet.
- Les démonstrations étudiantes utilisent uniquement des données fictives.

### React/Vite et les chemins

Le proxy retire le préfixe avant de transmettre la requête à Express : `/mon-projet/api/exemple` devient `/api/exemple`. Express peut donc conserver ses routes `/api` habituelles.

Le frontend doit connaître son chemin **lors du build**, pas seulement dans l’environnement du conteneur :

```dockerfile
ARG BASE_PATH=/
RUN npm run build -- --base=$BASE_PATH
```

Avec Vite, former les appels à l’API depuis cette base :

```js
fetch(`${import.meta.env.BASE_URL}api/exemple`)
```

Adapter aussi le `basename` si React Router est utilisé. Éviter les liens absolus `/api` ou `/assets` qui pointeraient vers la racine de la galerie. Un projet nécessitant des uploads, des WebSockets particuliers ou davantage de mémoire demande une adaptation ciblée à l’enseignant.

## Isolation et ressources

Chaque projet possède une base et un rôle PostgreSQL dédiés, deux réseaux Docker et des secrets différents. Son réseau web relie uniquement son application au proxy ; son réseau SQL relie uniquement son application au PostgreSQL partagé. Les règles `pg_hba.conf` limitent l’authentification à la paire rôle/base et au sous-réseau attribués. Les privilèges `PUBLIC` sur les bases sont retirés. Le carnet enseignant utilise ses propres réseaux et identifiants.

Les applications étudiantes partagent leur origine web entre elles lorsque leurs URL ne diffèrent que par le chemin. Elles ne doivent donc pas traiter de données confidentielles ou de vraies connexions nominatives. Le carnet enseignant, hébergé sur un autre hôte, reste séparé par les protections du navigateur, sa connexion et ses contrôles d’origine.

Chaque application est plafonnée à **192 Mio**, **0,25 CPU**, **128 processus** et 10 Mio de logs ; V8 reçoit un plafond de heap de 96 Mio. Ces plafonds ne constituent pas une réservation permanente. Vingt petites applications peu sollicitées peuvent tenir dans une mémoire totale inférieure à la somme des plafonds, mais aucune garantie n’est donnée sans mesure des applications réelles et de leur charge. Surveiller `docker stats`, les redémarrages/OOM, la RAM et le swap avant de décider d’une augmentation Jelastic. Aucune augmentation de ressources ou de facturation n’est automatique dans ce kit.

Les conteneurs partagent le noyau de l’hôte ; cette organisation vise une promotion encadrée et ne remplace pas une VM contre un attaquant déterminé. Aucun étudiant ne reçoit l’accès root, le socket Docker, le groupe Docker ou l’administration Jelastic.

## Installation et maintenance administratives

`deploy/platform/compose.yaml` fournit PostgreSQL et Caddy ; `compose.server.yaml` lance le carnet enseignant. Les fichiers `.env.platform`, `.env.server` et toutes les affectations réelles restent hors Git, protégés par root. Le proxy obtient les certificats HTTPS pour les deux noms d’hôtes fournis, dont les DNS doivent déjà pointer vers le serveur.

Le provisionnement étudiant nécessite Python 3, systemd et Docker Compose v2 supportant `up --wait`. Le script administratif doit être installé sur l’hôte et lancé comme root, après inspection de l’infrastructure. Il suppose les chemins `/opt/ihme-suivi` et `/opt/ihme-platform` et le conteneur PostgreSQL `ihme-platform-db-1`.

```sh
python3 /opt/ihme-suivi/deploy/platform/provision-students.py \
  --assignments /CHEMIN/PRIVE/affectations.json \
  --teacher-host suivi.exemple.fr --student-host projets.exemple.fr
```

Avant provisionnement, installer la configuration privée `.env.platform` dans `/opt/ihme-platform` et y définir `CADDY_CONFIG_PATH=/opt/ihme-platform/Caddyfile`. Le fichier Caddyfile généré et les secrets d’exploitation restent ainsi séparés des mises à jour du code.

Le tableau privé contient `id`, `title`, `slug`, `image_repository` et un `token` aléatoire d’au moins 32 caractères par projet. Ne pas stocker d’affectation réelle ou de jeton dans ce dépôt. Les réseaux utilisent des sous-réseaux `/28` de `172.29.0.0/16` ; vérifier l’absence de conflit avant installation. La stack et son manifeste de réseaux sont installés dans `/opt/ihme-platform`, hors du checkout du code, et doit être conservé lors de ses mises à jour :

```sh
cd /opt/ihme-platform
docker compose --project-name ihme-platform --env-file .env.platform \
  -f compose.yaml -f compose.students.networks.json up -d
```

L’API de déploiement est un service systemd root à entrée limitée, accessible seulement par un socket Unix monté dans Caddy. Elle ne reçoit ni commande shell, ni chemin Compose, ni nom d’image libre : seulement le digest du dépôt prédéfini pour le projet authentifié. Son code et les configurations doivent rester détenus par root, sans écriture par les étudiants. Les jetons attendus sont vérifiés par SHA-256 et comparaison à temps constant ; les en-têtes d’authentification ne sont pas journalisés par l’API. Les journaux de déploiement administratifs restent sur le serveur.

Pour révoquer un accès, remplacer le hash `/etc/ihme-students/pNN/.deploy-token.sha256` par celui d’un nouveau jeton aléatoire et remettre le nouveau fichier privé à son seul destinataire. La révocation n’arrête pas l’application déjà déployée. Un accès SSH à commande forcée reste une option du kit initial ; il n’est pas nécessaire au parcours HTTPS et aucun compte SSH étudiant n’est créé par défaut.

Les sauvegardes locales sont effectuées par `deploy/platform/backup.py` et le timer `ihme-backup.timer`, quotidiennement vers 03 h 20 Europe/Paris. Sept versions sont conservées par base ; les sessions du carnet sont exclues. Les dumps restent root uniquement dans `/var/backups/ihme`. Ce stockage local ne protège pas contre la perte de l’hôte : prévoir une copie chiffrée hors serveur et sauvegarder séparément les configurations privées nécessaires à la restauration des rôles et connexions.

## Vérifications

```sh
npm test
python3 -m unittest discover -s tests -p '*_test.py'
```

Les tests locaux couvrent les validations du déploiement, le refus des jetons d’un autre projet, le refus d’options supplémentaires, la sérialisation des déploiements et l’absence de noms/jetons dans la galerie générée. Sur le serveur, tester un projet fictif sain puis non sain, le rollback, la révocation, les refus SQL entre projets et l’isolation du carnet avant de distribuer les accès. Les dossiers d’accès privés ne doivent pas être envoyés sans instruction explicite de l’enseignant.
