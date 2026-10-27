#!/usr/bin/env python3
"""Galerie : noms autorisés, statistiques et miniatures ; retours explicitement publics, sans secrets."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
from gallery import render_gallery, render_pending, render_progress, checked_rows
from deployments import deployments


def update():
    os.umask(0o077)
    projects = checked_rows(json.loads(Path("/etc/ihme-gallery/projects.json").read_text()))
    script = """import {createDatabase} from './server/db.js'; import {exportProgress} from './server/progression.js'; const db=createDatabase(process.env.DATABASE_URL); try {const r=await db.query('SELECT p.repository_url,p.student_name,g.daily_activity,g.checked_at,g.error FROM projects p LEFT JOIN git_snapshots g ON g.project_id=p.id');console.log(JSON.stringify({rows:r.rows,reports:await exportProgress(db)}));} finally {await db.close();}"""
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
    exported = json.loads(output)
    by_repo = {
        row["repository_url"].rstrip("/").lower(): row for row in exported["rows"]
    }
    reports_by_repo = {
        row["repository_url"].rstrip("/").lower(): row["progression"] for row in exported["reports"]
    }
    progression = {}
    statistics = {}
    public_projects = []
    for project in projects:
        repo_key = project.get("repository", "").rstrip("/").lower()
        row = by_repo.get(repo_key)
        if repo_key in reports_by_repo:
            progression[project["id"]] = reports_by_repo[repo_key]
        public_projects.append(
            {
                "id": project["id"],
                "title": project["title"],
                "slug": project["slug"],
                "student_name": row.get("student_name", "") if row else "",
            }
        )
        if row and row.get("daily_activity"):
            # Liste blanche explicite. Aucune identité, URL, observation ou titre de commit.
            source = row["daily_activity"]
            statistics[project["id"]] = {
                "days": source.get("days"),
                "complete": source.get("complete", False),
                "stale": bool(row.get("error")),
            }
    # Index lisible par Node non privilégié, distinct des affectations administratives.
    site_folder = Path("/opt/ihme-platform/teacher-sites")
    site_folder.mkdir(mode=0o755, exist_ok=True)
    site_folder.chmod(0o755)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=site_folder, prefix=".sites-", suffix=".tmp", delete=False
    ) as output:
        json.dump([
            {key: project[key] for key in ("id", "repository", "slug")}
            for project in projects
        ], output)
        site_index = Path(output.name)
    site_index.chmod(0o644)
    site_index.replace(site_folder / "projects.json")
    folder = Path("/opt/ihme-platform/public")
    folder.mkdir(mode=0o755, exist_ok=True)
    folder.chmod(0o755)
    if (folder / "previews").is_dir():
        (folder / "previews").chmod(0o755)
    progress_root = folder / "progression"
    progress_root.mkdir(mode=0o755, exist_ok=True)
    progress_root.chmod(0o755)
    for project in public_projects:
        destination = progress_root / project["id"]
        destination.mkdir(mode=0o755, exist_ok=True)
        destination.chmod(0o755)
        with tempfile.NamedTemporaryFile(mode="w", dir=destination, prefix=".progress-", suffix=".tmp", delete=False) as page:
            page.write(render_progress(project, progression.get(project["id"])))
            target = Path(page.name)
        target.chmod(0o644)
        target.replace(destination / "index.html")
    with tempfile.NamedTemporaryFile(
        mode="w", dir=folder, prefix=".gallery-", suffix=".tmp", delete=False
    ) as output:
        output.write(render_gallery(public_projects, statistics, deployments(projects), progression))
        target = Path(output.name)
    target.chmod(0o644)
    target.replace(folder / "index.html")
    with tempfile.NamedTemporaryFile(
        mode="w", dir=folder, prefix=".pending-", suffix=".tmp", delete=False
    ) as output:
        output.write(render_pending())
        pending = Path(output.name)
    pending.chmod(0o644)
    pending.replace(folder / "_unavailable.html")
    print("Galerie actualisée : " + str(len(statistics)) + " graphiques disponibles.")


if __name__ == "__main__":
    update()
