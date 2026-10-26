#!/usr/bin/env python3
"""Point d'entrée SSH contraint, installé par root, jamais exécuté depuis un checkout étudiant."""

import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import tempfile

BASE = Path("/etc/ihme-students")
TEMPLATE = Path("/opt/ihme-platform/compose.student.yaml")


def validate_request(project, digest):
    if not re.fullmatch(r"p[0-9]{2}", project):
        raise ValueError("Identifiant de projet invalide.")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError(
            "Digest SHA-256 attendu ; les tags et options Docker sont interdits."
        )


def validate_image_config(config):
    # Une déclaration VOLUME de l’image créerait des volumes anonymes même avec read_only.
    if config.get("Volumes"):
        raise ValueError(
            "Images déclarant des volumes interdites ; demander une adaptation à l’enseignant."
        )


def trusted(path):
    """Les répertoires parents du chemin sont également administrés par root."""
    for entry in [path, *path.parents]:
        if entry.is_symlink():
            raise ValueError("Lien symbolique interdit dans la configuration.")
        info = entry.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError(
                "Configuration non protégée : propriétaire root et aucune écriture groupe/autres requis."
            )


def deploy(project, digest):
    validate_request(project, digest)
    if os.geteuid() != 0:
        raise ValueError(
            "Utiliser uniquement le point d’entrée sudo configuré par l’administrateur."
        )
    folder = BASE / project
    config = folder / ".env.student"
    trusted(config)
    trusted(TEMPLATE)
    state = folder / ".current-image-digest"
    if state.exists():
        trusted(state)
        previous = state.read_text().strip()
        validate_request(project, previous)
    else:
        previous = None
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
        "IMAGE_DIGEST": digest,
    }
    command = [
        "docker",
        "compose",
        "--project-name",
        "ihme-" + project,
        "--env-file",
        str(config),
        "-f",
        str(TEMPLATE),
    ]

    def compose(*args):
        # Ne pas afficher les messages Docker : ils peuvent citer la configuration de l’application.
        return subprocess.run(
            command + list(args),
            env=environment,
            cwd=folder,
            check=True,
            text=True,
            capture_output=True,
            timeout=180,
        ).stdout.strip()

    with (folder / ".deploy.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stamp = folder / ".last-attempt"
        if stamp.exists() and time.time() - stamp.stat().st_mtime < 60:
            raise ValueError("Un déploiement par minute maximum.")
        stamp.touch(mode=0o600)
        compose("config", "--quiet")
        registry_token = os.environ.pop("IHME_REGISTRY_TOKEN", "")
        with tempfile.TemporaryDirectory(prefix="ihme-pull-") as auth:
            if registry_token:
                reference = compose("config", "--images").strip()
                if not reference.startswith("ghcr.io/"):
                    raise ValueError("Le jeton éphémère fourni est réservé à ghcr.io.")
                environment["DOCKER_CONFIG"] = auth
                subprocess.run(
                    [
                        "docker",
                        "login",
                        "ghcr.io",
                        "--username",
                        reference.split("/")[1],
                        "--password-stdin",
                    ],
                    input=registry_token,
                    env=environment,
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=30,
                )
            compose("pull", "app")
        environment.pop("DOCKER_CONFIG", None)
        reference = compose("config", "--images").strip()
        inspected = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{json .Config}}", reference],
            env=environment,
            check=True,
            text=True,
            capture_output=True,
            timeout=15,
        )
        validate_image_config(json.loads(inspected.stdout))
        try:
            compose(
                "up",
                "-d",
                "--no-build",
                "--pull",
                "never",
                "--wait",
                "--wait-timeout",
                "60",
                "app",
            )
        except subprocess.SubprocessError:
            if previous:
                environment["IMAGE_DIGEST"] = previous
                compose(
                    "up",
                    "-d",
                    "--no-build",
                    "--pull",
                    "never",
                    "--wait",
                    "--wait-timeout",
                    "60",
                    "app",
                )
                raise ValueError(
                    "Nouvelle version non saine ; version précédente rétablie."
                )
            compose("stop", "app")
            raise ValueError("Première version non saine ; application arrêtée.")
        pending = folder / ".current-image-digest.new"
        with pending.open("w") as target:
            os.chmod(pending, 0o600)
            target.write(digest + "\n")
        pending.replace(state)
    print("Application " + project + " déployée et vérifiée.")


def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError("Un seul identifiant de projet attendu.")
        # Le digest vient uniquement de stdin. SSH_ORIGINAL_COMMAND et les variables du client sont ignorés.
        signal.alarm(20)
        digest = sys.stdin.buffer.read(80).decode("ascii").strip()
        signal.alarm(0)
        deploy(sys.argv[1], digest)
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as error:
        print(
            (
                str(error)
                if isinstance(error, ValueError)
                else "Échec du déploiement ; contacter l’enseignant."
            ),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
