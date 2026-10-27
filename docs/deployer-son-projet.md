# Publier puis déployer son projet IHME

Cette fiche concerne les projets **React + Express + PostgreSQL**. Le même parcours est disponible pour le carnet enseignant et les espaces étudiants : GitHub construit une image, puis le serveur exécute la version explicitement choisie.

## Ce qui se passe

```text
Code du projet → push GitHub → construction Docker → image dans GHCR
                                                        ↓
                                  bouton « Déployer » → serveur IHME
```

Une image Docker contient l’application préparée pour son exécution. Son **digest** est l’empreinte de ce contenu, par exemple `sha256:…`. Le commit Git identifie le code ; le digest identifie l’image complète, avec ses dépendances. Le nom `latest` peut changer : le serveur du cours exige donc un digest précis.

Un push publie une image sans changer l’application sur le serveur. La mise en production est une action distincte, volontaire.

## Pour le projet de suivi de l’enseignant

Le Dockerfile existe déjà. Le workflow `.github/workflows/publish.yml` est configuré pour construire une image après chaque push sur `main` et la publier dans `ghcr.io/cedrictisseyre/ihme-suivi`.

Après une modification :

```sh
git add LES_FICHIERS_MODIFIES
git commit -m "Description de la modification"
git push
```

1. Ouvrir l’onglet **Actions** du dépôt GitHub.
2. Ouvrir **Construire et publier l’image**. La construction issue du push affiche le commit et le digest dans son résumé.
3. Pour mettre une version en ligne, cliquer **Run workflow**, choisir `main`, cocher **Déployer cette version après construction**, puis lancer.
4. Attendre la réussite du workflow et vérifier le carnet. `/api/health` affiche la révision Git du code exécuté.

Le jeton enseignant est enregistré dans le secret GitHub Actions `IHME_DEPLOY_TOKEN`. L’adresse est dans la variable `IHME_DEPLOY_URL`. Ces paramètres sont distincts du mot de passe de connexion au carnet. Le serveur télécharge l’image du seul dépôt autorisé, sauvegarde la base, exécute la migration et contrôle la santé de l’application. Si la nouvelle application ne démarre pas correctement, il relance l’image précédente. Les migrations doivent rester compatibles ; ce retour arrière ne restaure pas automatiquement la base.

Le même accès peut aussi être utilisé en ligne de commande avec le fichier privé `deploy.curl` du dossier enseignant : `curl --config deploy.curl --data '{"digest":"sha256:..."}'`. Cette variante suppose une image publique ou des droits de lecture déjà configurés côté serveur. Le bouton GitHub Actions fonctionne aussi pour une image GHCR privée grâce au jeton de registre temporaire du job.

## Consigne à transmettre aux étudiants

> Préparez votre projet pour son déploiement. L’application doit servir React compilé et l’API `/api` sur le port 3000, utiliser `DATABASE_URL` fourni par le serveur et fonctionner sous le chemin web qui vous a été attribué. Utilisez uniquement des données fictives. Ne mettez aucun mot de passe ni fichier d’accès dans Git.
>
> Ajoutez le Dockerfile, le fichier `.dockerignore`, le workflow GitHub Actions et le petit client de déploiement fournis. Configurez les paramètres privés reçus de l’enseignant, poussez votre code, puis vérifiez la construction de l’image dans Actions. Lancez ensuite manuellement le workflow avec l’option « Déployer » et vérifiez votre application en ligne.

### 1. Ajouter les fichiers fournis

Copier le contenu de [`docs/templates/student/`](templates/student/) à la **racine de votre propre dépôt**. La structure attendue est :

```text
Dockerfile
.dockerignore
.github/workflows/publish.yml
deploy/request.py
package.json
package-lock.json
index.html
src/
server/index.js
```

Le Dockerfile est un exemple pour un projet regroupé à la racine. Si votre React et votre serveur ont des `package.json` séparés ou si votre fichier serveur porte un autre nom, adaptez ses commandes `COPY`, installation et démarrage avec l’enseignant. N’utilisez pas un Dockerfile qui ne correspond pas à votre structure.

Le workflow déclenche la construction sur `main` ou `master`. Il utilise le `GITHUB_TOKEN` généré automatiquement par GitHub pour publier l’image dans GHCR : aucun compte Docker Hub ni jeton personnel GitHub n’est nécessaire.

### 2. Configurer trois paramètres dans GitHub

Dans **Settings → Secrets and variables → Actions** de votre propre dépôt :

| Emplacement | Nom | Valeur |
|---|---|---|
| **Secrets** | `IHME_DEPLOY_TOKEN` | Votre jeton personnel remis par l’enseignant |
| **Variables** | `IHME_DEPLOY_URL` | Votre URL complète de déploiement, terminée par `/__deploy/pNN` |
| **Variables** | `IHME_BASE_PATH` | Votre chemin web, par exemple `/mon-projet/` |

#### Ajouter le secret de déploiement

1. Ouvrir l’onglet **Secrets**.
2. Descendre jusqu’à **Repository secrets**, puis cliquer sur **New repository secret**. Utiliser les secrets du dépôt ; aucun environnement GitHub n’est nécessaire pour le workflow fourni.
3. Dans **Name**, saisir exactement `IHME_DEPLOY_TOKEN`.
4. Dans **Secret**, coller uniquement la valeur du jeton personnel remis par l’enseignant, sans guillemets ni espaces ajoutés.
5. Cliquer sur **Add secret**.

Le champ **Name** contient le nom fixe `IHME_DEPLOY_TOKEN`. Le champ **Secret** contient votre jeton privé. Ne pas coller le jeton dans **Name**, ni saisir une ligne complète comme `IHME_DEPLOY_TOKEN=…` dans l’un des champs.

#### Ajouter les deux variables

1. Revenir dans **Settings → Secrets and variables → Actions**, puis ouvrir l’onglet **Variables**.
2. Cliquer sur **New repository variable**.
3. Dans **Name**, saisir exactement `IHME_DEPLOY_URL`. Dans **Value**, coller l’URL de déploiement personnelle fournie, terminée par `/__deploy/pNN` avec votre numéro de projet. Cliquer sur **Add variable**.
4. Cliquer à nouveau sur **New repository variable**.
5. Dans **Name**, saisir exactement `IHME_BASE_PATH`. Dans **Value**, saisir le chemin web attribué, par exemple `/mon-projet/`, avec les barres obliques initiale et finale. Cliquer sur **Add variable**.

Vérifier que vous avez **un secret dans Secrets et deux variables dans Variables**, avec les trois noms exacts du tableau. Le workflow fourni lit l’URL et le chemin dans les variables : les créer uniquement dans **Secrets** ne suffit pas. Le `GITHUB_TOKEN` est fourni automatiquement par GitHub ; ne pas le créer manuellement.

#### Erreur « Secret names can only contain alphanumeric characters… »

Ce message concerne le champ **Name**, pas la valeur du jeton. Un nom de secret accepte uniquement des lettres, des chiffres et des underscores `_`, sans espaces, tirets, accents, signes `=` ni barres obliques. Il ne doit pas commencer par un chiffre ni par le préfixe réservé `GITHUB_`.

Effacer le contenu du champ **Name** et saisir `IHME_DEPLOY_TOKEN`, sans guillemets ni espace avant ou après. Coller le jeton dans le champ **Secret**, puis cliquer sur **Add secret**. Les règles de nommage ne demandent pas de modifier les caractères de votre jeton.

Ne jamais partager la valeur du secret dans une capture d’écran. Pour demander de l’aide, montrer uniquement les noms des paramètres et le message d’erreur.

Les valeurs réelles figurent dans votre dossier d’accès privé. Ne copiez pas les valeurs d’un autre projet. Le dépôt d’image déduit de `ghcr.io/PROPRIETAIRE/DEPOT` doit correspondre au dépôt autorisé par l’enseignant ; demander une mise à jour si vous renommez votre dépôt.

Une image GHCR est initialement privée. Le workflow transmet son jeton GitHub temporaire au serveur uniquement pendant le téléchargement, sans le conserver. Ce jeton expire à la fin du job. Vous n’avez donc pas besoin de rendre votre image publique pour utiliser ce parcours. Gardez vos fichiers secrets hors du contexte Docker grâce à `.dockerignore`.

### 3. Adapter le chemin et vérifier l’API

Avec Vite, le Dockerfile reçoit `BASE_PATH` pendant la construction. Former les appels à l’API ainsi :

```js
fetch(`${import.meta.env.BASE_URL}api/exemple`)
```

Si React Router est utilisé, configurer aussi son `basename`. Le proxy retire le préfixe avant d’appeler Express : `/mon-projet/api/exemple` devient `/api/exemple` dans le serveur Node.

Ajouter une route de santé sans information confidentielle :

```js
app.get('/api/health', async (req, res) => {
  try {
    await pool.query('SELECT 1');
    res.json({ status: 'ok' });
  } catch {
    res.status(503).json({ status: 'unavailable' });
  }
});
```

Limiter le pool PostgreSQL à 4 connexions. Créer les tables nécessaires avec une migration idempotente sur votre propre base ; le serveur du cours n’invente pas votre schéma SQL. Vérifier que Node écoute sur `0.0.0.0:3000` et que vos fichiers sont lisibles par l’utilisateur 1000 du conteneur.

### 4. Publier puis déployer

Faire un commit et un push. Dans **Actions**, attendre le succès de **Construire et publier l’image**. Pour mettre cette version en ligne, lancer **Run workflow**, cocher **Déployer cette version après construction** et attendre la réussite. Ouvrir ensuite votre URL de projet.

Ne partagez jamais le jeton de déploiement dans une capture d’écran, un rapport public ou une issue. La construction ne reçoit pas les observations du carnet enseignant ni les identifiants des autres projets.

## Si le déploiement échoue avec HTTP 422

Le serveur a accepté l’authentification, mais n’a pas pu terminer le déploiement. Ce statut seul ne permet pas de connaître la cause. Le client à jour indique si l’échec concerne la configuration Docker, la connexion à GHCR, le téléchargement de l’image ou la santé de l’application.

Recopier `deploy/request.py` depuis le modèle étudiant pour bénéficier de ces messages. L’enseignant doit également installer les versions à jour de `deploy/students/api.py` et `deploy/students/deploy.py` sur le serveur et redémarrer le service `ihme-deploy`. Un ancien serveur continue de renvoyer un message générique.

Pour un échec de téléchargement, vérifier la correspondance entre le dépôt GHCR autorisé sur le serveur et celui publié par le workflow, ainsi que les droits du package. Pour une application non saine, l’enseignant doit examiner ses journaux : démarrage de Node, accès PostgreSQL et réponse de `/api/health` sur le port 3000. Ne pas publier les journaux contenant des identifiants.

## Cas du projet hébergé sur GitLab

Le modèle GitHub Actions ne s’exécute pas sur GitLab. Un projet GitLab nécessite un pipeline `.gitlab-ci.yml` et son registre, ou une migration volontaire vers un dépôt GitHub. Ne changer ni forge ni visibilité sans l’auteur du projet. L’accès de déploiement reste utilisable en transmettant le digest ; les identifiants d’un registre GitLab privé doivent être configurés séparément côté serveur. Le jeton temporaire `registry_token` de ce modèle est réservé à GHCR.

## Sources

- [GitHub : publier des images Docker](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
- [GitHub : accès et visibilité des packages](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility)
- [GitHub : ajouter un secret de dépôt](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [GitHub : règles de nommage des secrets](https://docs.github.com/en/actions/reference/security/secrets)
