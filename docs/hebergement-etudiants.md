# Héberger les projets étudiants sur le Docker Engine du cours

Ce kit prépare l’hébergement sur le même hôte que le carnet enseignant. **Il n’est pas encore installé sur le serveur.** L’administrateur doit d’abord inspecter les ressources, les réseaux, PostgreSQL, le proxy HTTPS et la version de Docker Compose. Aucun compte étudiant ni accès serveur n’est créé par ces fichiers.

## Modèle d’accès retenu

Chaque projet reçoit un identifiant technique (`p01`, `p02`…), une URL HTTPS, une application conteneurisée, une base PostgreSQL et un rôle SQL dédiés. Les noms et mails réels restent dans la base privée du carnet et dans la correspondance administrative hors Git.

Les étudiants construisent leurs images dans leur CI ou sur leur ordinateur et demandent le déploiement d’un **digest immuable** dans un dépôt d’images choisi par l’enseignant. Le serveur n’exécute aucun Dockerfile étudiant en tant qu’administrateur. Les migrations de leur base sont effectuées par leur application avec leur seul rôle SQL.

Un accès Docker partagé, un socket `/var/run/docker.sock` ou un compte membre du groupe `docker` donnerait le contrôle de toutes les applications. Le kit fournit donc un accès SSH limité à une commande de déploiement, par clé et par projet. Il ne permet ni shell, ni tunnel, ni commande Compose arbitraire. Aucun accès n’est accordé aux observations enseignant ou à la configuration d’un autre projet.

Les conteneurs partagent néanmoins le noyau de l’hôte : cette organisation convient à une promotion encadrée, et ne constitue pas une isolation équivalente à une VM contre un attaquant déterminé. Ne pas donner un accès administrateur Jelastic à toute la promotion.

## Réseaux et PostgreSQL partagé

Pour chaque projet, créer deux réseaux Docker distincts, administrés par l’enseignant :

- `ihme-p01-web` : uniquement le proxy et l’application p01 ; aucune autre application étudiante.
- `ihme-p01-db` : uniquement PostgreSQL et l’application p01, avec l’alias `postgres-p01` pour la base.

Le proxy est connecté à chaque réseau web et route l’URL attribuée vers `p01:3000`. PostgreSQL est connecté à chaque réseau de base. Ne pas connecter les applications étudiantes aux réseaux du carnet enseignant. Ne pas publier de port SQL ou applicatif sur Internet ; seul le proxy HTTPS doit être public.

Créer une base `ihme_p01` et un rôle `ihme_p01`, sans SUPERUSER, CREATEDB ou CREATEROLE. Le rôle possède uniquement sa base. L’administrateur doit vérifier les droits `PUBLIC`, les autres bases et `pg_hba.conf` : un rôle ne doit pouvoir s’authentifier que sur la base de son projet. Utiliser des entrées spécifiques par base/rôle/réseau avant un refus par défaut ; vérifier les règles existantes sans casser les autres services. Configurer aussi une limite de connexions par rôle et un `statement_timeout` adapté.

Ne pas transmettre les identifiants PostgreSQL du carnet enseignant. Les secrets SQL étudiants sont installés par l’administrateur dans un fichier root protégé sur le serveur et transmis uniquement à leur application au lancement. Leur éventuelle distribution aux étudiants nécessite un canal privé distinct, jamais une issue GitHub publique.

## Installation administrative du point d’entrée

Prérequis à vérifier sur l’hôte : Python 3, sudo, OpenSSH et Docker Compose v2 supportant `up --wait`. Le mécanisme doit être essayé sur une application fictive avant de distribuer les accès.

1. Installer `deploy/students/compose.student.yaml` dans `/opt/ihme-platform/compose.student.yaml` et `deploy/students/deploy.py` dans `/usr/local/sbin/ihme-student-deploy`. Les fichiers et tous leurs répertoires parents doivent appartenir à root et ne pas être modifiables par le groupe ou les autres utilisateurs. Le script doit être exécutable.
2. Créer `/etc/ihme-students/p01/`, appartenant à root (0700), et son `.env.student` (0600), selon `deploy/students/env.student.example`. Définir le dépôt d’images **exact** du projet, l’origine HTTPS, les deux réseaux et sa seule connexion SQL. Le fichier est détenu par root et n’est jamais modifiable par l’étudiant.
3. Créer un compte système dédié `ihme-deploy`, sans mot de passe utilisable et sans appartenance au groupe Docker. Aucun accès interactif ne doit être accordé. Configurer OpenSSH pour désactiver l’authentification par mot de passe de ce compte et lire ses clés dans un fichier détenu par root, par exemple `/etc/ssh/authorized_keys/ihme-deploy`.
4. Ajouter chaque **clé publique fournie par l’étudiant** avec une commande forcée et des restrictions. Exemple fictif :

```text
restrict,command="sudo -n /usr/local/sbin/ihme-student-deploy p01" ssh-ed25519 CLE_PUBLIQUE_DE_P01
```

5. Ajouter via `visudo` une règle sudo limitée aux seules commandes nécessaires, sans joker ni argument libre. Exemple pour p01 :

```text
ihme-deploy ALL=(root) NOPASSWD: /usr/local/sbin/ihme-student-deploy p01
```

6. Vérifier `sshd -t` et `visudo -c` avant rechargement ; garder la connexion administrateur existante ouverte et tester une nouvelle connexion. Si Jelastic ne permet pas ces comptes/contrôles SSH, ne pas élargir l’accès à son compte root : conserver le déploiement assuré par l’enseignant en attendant un point d’entrée compatible.

Le point d’entrée accepte uniquement `pNN` et un digest `sha256:` suivi de 64 caractères hexadécimaux. Il ne charge aucune variable envoyée par SSH et ne lance aucun shell pour interpréter le digest. Compose lit une configuration root prédéfinie : l’étudiant ne peut choisir ni volumes, ni privilèges, ni réseaux, ni secrets. Un verrou empêche les déploiements simultanés d’un projet ; une limite d’une tentative par minute réduit les répétitions.

## Contrat de l’application étudiante

Le projet React/Express/PostgreSQL doit :

- servir React compilé et `/api` sur `0.0.0.0:3000` ;
- utiliser `DATABASE_URL`, `PORT` et `NODE_ENV` fournis à l’exécution ;
- démarrer sous UID/GID 1000, avec un système de fichiers en lecture seule et `/tmp` temporaire ;
- répondre à `GET /api/health` sans divulguer de secret et vérifier sa connexion SQL ;
- effectuer uniquement des migrations prévues sur sa propre base ;
- ne contenir aucun secret dans l’image ou le dépôt Git.

Les images déclarant des volumes Docker sont refusées pour éviter la création de stockage anonyme non prévu. Surveiller aussi l’espace occupé par les images du registre, les volumes SQL et les sauvegardes ; les limites mémoire/CPU ne sont pas des quotas de disque.

Le kit limite chaque application à 256 Mio, 0,25 CPU, 128 processus et 10 Mio de logs. Ces limites sont **provisoires** : 20 applications peuvent représenter jusqu’à 5 Gio de mémoire, hors PostgreSQL, proxy, carnet et système. Vérifier la capacité et le plafond de facturation Jelastic avant activation de toute la promotion. Une application nécessitant des uploads ou plus de mémoire doit faire l’objet d’une adaptation administrative ciblée.

Le script revient au digest précédent si la nouvelle version n’atteint pas un état sain ; pour un premier déploiement défaillant, il arrête l’application. Ce retour arrière ne restaure pas les données SQL : les migrations étudiantes doivent être compatibles, et les sauvegardes restent nécessaires.

## Déployer depuis un poste étudiant

Après la mise en place et l’attribution des accès par l’enseignant :

```sh
# Construire et publier dans le dépôt d’images exact attribué par l’enseignant.
# Le serveur cible doit être confirmé avant de choisir --platform.
docker buildx build --platform linux/amd64 --tag ghcr.io/compte-exemple/projet-exemple:version --push .
# Copier le digest retourné, puis remplacer DIGEST et HOTE/PORT par les valeurs attribuées.
printf '%s\n' 'sha256:DIGEST' | ssh -T -p PORT ihme-deploy@HOTE
```

Vérifier l’empreinte de l’hôte via l’enseignant avant la première connexion. Chaque clé est liée à un seul projet par la configuration serveur. L’accès ne permet pas de consulter les logs ou d’obtenir un terminal ; au départ, l’enseignant consulte les logs filtrés du projet. Une interface de logs ou un accès supplémentaire ne doit être ajouté qu’avec des contrôles spécifiques.

Pour un dépôt d’images privé, les identifiants de lecture sont administrés côté serveur dans la configuration du registre. Aucun jeton global d’écriture ne doit être distribué. Les clés privées restent sur le poste étudiant ou dans les secrets de sa CI ; ne pas les copier dans le carnet de suivi.

## Recette avant ouverture aux étudiants

Sur un projet fictif : déployer une image saine, puis une image défaillante et vérifier le retour arrière. Vérifier que les clés ne permettent ni shell, ni forwarding, ni déploiement sur p02. Essayer un digest invalide. Confirmer les plafonds de ressources et l’absence de socket Docker/montage hôte dans le conteneur. Depuis p01, vérifier que la base et les secrets du carnet et de p02 ne sont pas accessibles. Tester la sauvegarde/restauration SQL et la révocation d’une clé.

Tests locaux du validateur (sans serveur) : `python3 -m unittest discover -s tests -p '*_test.py'`.
