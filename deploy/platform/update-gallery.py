#!/usr/bin/env python3
"""Exporte uniquement des comptes journaliers de commits, jamais les observations."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
from gallery import render_gallery


def update():
    os.umask(0o077)
    projects = json.loads(Path("/etc/ihme-gallery/projects.json").read_text())
    script = """import {createDatabase} from './server/db.js'; const db=createDatabase(process.env.DATABASE_URL); try {const r=await db.query('SELECT p.repository_url,g.daily_activity,g.checked_at,g.error FROM projects p LEFT JOIN git_snapshots g ON g.project_id=p.id');console.log(JSON.stringify(r.rows));} finally {await db.close();}"""
    output = subprocess.check_output(
        [
            "docker",
            "exec",
            "ihme-suivi-app-1",
            "node",
            "--input-type=module",
            "-e",
            script,
        ],
        text=True,
        timeout=30,
    )
    by_repo = {
        row["repository_url"].rstrip("/").lower(): row for row in json.loads(output)
    }
    statistics = {}
    for project in projects:
        row = by_repo.get(project.get("repository", "").rstrip("/").lower())
        if row and row.get("daily_activity"):
            # Liste blanche explicite. Aucune identité, URL, observation ou titre de commit.
            source = row["daily_activity"]
            statistics[project["id"]] = {
                "days": source.get("days"),
                "complete": source.get("complete", False),
                "stale": bool(row.get("error")),
            }
    folder = Path("/opt/ihme-platform/public")
    folder.mkdir(mode=0o755, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=folder, prefix=".gallery-", suffix=".tmp", delete=False
    ) as output:
        output.write(render_gallery(projects, statistics))
        target = Path(output.name)
    target.chmod(0o644)
    target.replace(folder / "index.html")
    print("Galerie actualisée : " + str(len(statistics)) + " graphiques disponibles.")


if __name__ == "__main__":
    update()
