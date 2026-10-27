"""Métadonnées publiques autorisées des déploiements ; aucune lecture de secrets Docker."""

from pathlib import Path
import re
import subprocess

BASE = Path("/etc/ihme-students")
PUBLIC = Path("/opt/ihme-platform/public")


def thumbnail_name(project, digest):
    if not re.fullmatch(r"p[0-9]{2}", project) or not re.fullmatch(
        r"sha256:[a-f0-9]{64}", digest
    ):
        raise ValueError("Identifiant de miniature invalide.")
    return project + "-" + digest[7:] + ".jpg"


def deployments(projects):
    ids = subprocess.check_output(
        ["docker", "ps", "-aq", "--filter", "label=com.docker.compose.service=app"],
        text=True,
        timeout=15,
    ).split()
    running = {}
    if ids:
        output = subprocess.check_output(
            [
                "docker",
                "inspect",
                "--format",
                '{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} {{index .Config.Labels "com.docker.compose.project"}}',
                *ids,
            ],
            text=True,
            timeout=15,
        )
        for line in output.splitlines():
            active, health, project = line.split()
            if re.fullmatch(r"ihme-p[0-9]{2}", project):
                running[project[5:]] = active == "true" and health == "healthy"
    result = {}
    for project in projects:
        identity = project["id"]
        if not re.fullmatch(r"p[0-9]{2}", identity):
            raise ValueError("Projet invalide.")
        state = BASE / identity / ".current-image-digest"
        if not state.is_file():
            continue
        digest = state.read_text().strip()
        filename = thumbnail_name(identity, digest)
        data = {
            "published": True,
            "available": running.get(identity, False),
            "digest": digest,
        }
        if (PUBLIC / "previews" / filename).is_file():
            data["thumbnail"] = "/previews/" + filename
        result[identity] = data
    return result
