#!/usr/bin/env python3
"""Déploiement du carnet : seul le digest de son dépôt GHCR fixe est accepté."""

import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path("/opt/ihme-suivi")
CONFIG = ROOT / ".env.server"
COMPOSE = ROOT / "compose.server.yaml"
STATE = Path("/etc/ihme-teacher")
REPOSITORY = "ghcr.io/cedrictisseyre/ihme-suivi"


def validate_digest(digest):
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("Digest SHA-256 attendu.")


def trusted(path):
    for entry in [path, *path.parents]:
        info = entry.stat()
        if entry.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("Configuration root protégée requise.")


def updated_config(content, image, version):
    lines = content.splitlines()
    for key, value in [("APP_IMAGE", image), ("APP_VERSION", version)]:
        lines = [line for line in lines if not line.startswith(key + "=")]
        lines.append(key + "=" + value)
    return "\n".join(lines) + "\n"


def deploy(digest):
    validate_digest(digest)
    if os.geteuid() != 0:
        raise ValueError("Administration requise.")
    for path in [CONFIG, COMPOSE, STATE]:
        trusted(path)
    os.umask(0o077)
    with (STATE / ".deploy.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stamp = STATE / ".last-attempt"
        if stamp.exists() and time.time() - stamp.stat().st_mtime < 60:
            raise ValueError("Une tentative par minute maximum.")
        stamp.touch(mode=0o600)
        previous = CONFIG.read_text()
        values = dict(
            line.split("=", 1)
            for line in previous.splitlines()
            if "=" in line and not line.startswith("#")
        )
        environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/root",
            "APP_IMAGE": REPOSITORY + "@" + digest,
        }
        command = [
            "docker",
            "compose",
            "--project-name",
            "ihme-suivi",
            "--env-file",
            str(CONFIG),
            "-f",
            str(COMPOSE),
        ]

        def compose(*args):
            return subprocess.run(
                command + list(args),
                env=environment,
                cwd=ROOT,
                text=True,
                check=True,
                capture_output=True,
                timeout=180,
            ).stdout

        registry_token = os.environ.pop("IHME_REGISTRY_TOKEN", "")
        with tempfile.TemporaryDirectory(prefix="ihme-teacher-pull-") as auth:
            if registry_token:
                environment["DOCKER_CONFIG"] = auth
                subprocess.run(
                    [
                        "docker",
                        "login",
                        "ghcr.io",
                        "--username",
                        "cedrictisseyre",
                        "--password-stdin",
                    ],
                    input=registry_token,
                    text=True,
                    env=environment,
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
            compose("pull", "app")
        environment.pop("DOCKER_CONFIG", None)
        metadata = json.loads(
            subprocess.check_output(
                ["docker", "image", "inspect", environment["APP_IMAGE"]], text=True
            )
        )[0]["Config"]
        if metadata.get("Volumes"):
            raise ValueError("L’image du carnet ne doit pas déclarer de volume.")
        revision = (metadata.get("Labels") or {}).get(
            "org.opencontainers.image.revision", ""
        )
        version = (
            revision[:12] if re.fullmatch(r"[a-f0-9]{40}", revision) else digest[7:19]
        )
        environment["APP_VERSION"] = version
        # Sauvegarde avant toute migration. Les identifiants ne figurent pas dans les arguments.
        backup = Path("/var/backups/ihme") / (
            "ihme_suivi-predeploy-"
            + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            + ".dump"
        )
        backup.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with backup.open("wb") as output:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "ihme-platform-db-1",
                    "pg_dump",
                    "-U",
                    "platform_admin",
                    "-d",
                    "ihme_suivi",
                    "-Fc",
                    "--no-owner",
                    "--no-acl",
                    "--exclude-table-data=public.sessions",
                ],
                stdout=output,
                stderr=subprocess.PIPE,
                check=True,
                timeout=120,
            )
        # L’API actuelle reste en service si la migration échoue.
        compose("run", "--rm", "--no-deps", "--pull", "never", "migrate")
        try:
            compose(
                "up",
                "-d",
                "--no-deps",
                "--no-build",
                "--pull",
                "never",
                "--wait",
                "--wait-timeout",
                "60",
                "app",
            )
            temporary = CONFIG.with_suffix(".server.next")
            temporary.write_text(
                updated_config(previous, environment["APP_IMAGE"], version)
            )
            temporary.chmod(0o600)
            temporary.replace(CONFIG)
        except (subprocess.SubprocessError, OSError):
            environment["APP_IMAGE"] = values["APP_IMAGE"]
            environment["APP_VERSION"] = values.get("APP_VERSION", "previous")
            compose(
                "up",
                "-d",
                "--no-deps",
                "--no-build",
                "--pull",
                "never",
                "--wait",
                "--wait-timeout",
                "60",
                "app",
            )
            raise ValueError(
                "Version non saine ; version précédente rétablie. La base n’a pas été restaurée automatiquement."
            )
    print("Carnet enseignant déployé et vérifié.")


if __name__ == "__main__":
    try:
        if len(sys.argv) != 1:
            raise ValueError("Aucun argument libre accepté.")
        signal.alarm(20)
        digest = sys.stdin.buffer.read(80).decode("ascii").strip()
        signal.alarm(0)
        deploy(digest)
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError):
        print(
            "Déploiement du carnet refusé ou non sain. Consulter le journal administrateur.",
            file=sys.stderr,
        )
        sys.exit(1)
