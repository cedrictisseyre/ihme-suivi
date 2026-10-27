#!/usr/bin/env python3
"""Capture périodique des seules pages publiques des projets déployés, dans un navigateur isolé."""

import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
from deployments import deployments, thumbnail_name


def refresh():
    os.umask(0o077)
    with open("/run/ihme-previews.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        root = Path("/opt/ihme-platform")
        projects = json.loads(Path("/etc/ihme-gallery/projects.json").read_text())
        states = deployments(projects)
        output = root / "public/previews"
        output.mkdir(parents=True, exist_ok=True, mode=0o755)
        output.chmod(0o755)
        targets = []
        for project in projects:
            state = states.get(project["id"], {})
            if not state.get("available"):
                continue
            destination = output / thumbnail_name(project["id"], state["digest"])
            if (
                destination.exists()
                and time.time() - destination.stat().st_mtime < 86400
            ):
                continue
            targets.append(
                {
                    "id": project["id"],
                    "digest": state["digest"],
                    "path": "/" + project["slug"] + "/",
                }
            )
        attempts_path = root / "preview-attempts.json"
        attempts = (
            json.loads(attempts_path.read_text()) if attempts_path.exists() else {}
        )
        targets = sorted(targets, key=lambda p: attempts.get(p["id"], 0))[:6]
        if not targets:
            print("Miniatures à jour.")
            return
        attempts.update({p["id"]: time.time() for p in targets})
        attempts_path.write_text(json.dumps(attempts))
        config = dict(
            line.split("=", 1)
            for line in (root / ".env.platform").read_text().splitlines()
            if "=" in line and not line.startswith("#")
        )
        origin = config["STUDENT_ORIGIN"].rstrip("/")
        with tempfile.TemporaryDirectory(prefix="ihme-preview-", dir=root) as work:
            staging = Path(work)
            staging.chmod(0o700)
            os.chown(staging, 1000, 1000)
            container = "ihme-previews-" + uuid.uuid4().hex[:12]
            command = [
                "docker",
                "run",
                "--rm",
                "--name",
                container,
                "--init",
                "-i",
                "--user",
                "1000:1000",
                "-e",
                "HOME=/tmp/home",
                "-e",
                "XDG_CACHE_HOME=/tmp/cache",
                "--network",
                "ihme-previews",
                "--cap-drop",
                "ALL",
                "--cap-add",
                "SYS_CHROOT",
                "--security-opt",
                "no-new-privileges:true",
                "--security-opt",
                "seccomp=" + str(root / "preview-seccomp.json"),
                "--read-only",
                "--memory",
                "512m",
                "--cpus",
                "0.5",
                "--pids-limit",
                "192",
                "--shm-size",
                "128m",
                "--tmpfs",
                "/tmp:rw,nosuid,size=128m",
                "-v",
                str(staging) + ":/output:rw",
                "ihme-previews:1.64.1",
            ]
            try:
                result = subprocess.run(
                    command,
                    input=json.dumps({"origin": origin, "projects": targets}),
                    text=True,
                    check=True,
                    capture_output=True,
                    timeout=600,
                )
            except subprocess.CalledProcessError as error:
                print(error.stderr[-2000:])
                raise
            finally:
                subprocess.run(
                    ["docker", "rm", "-f", container], capture_output=True, timeout=30
                )
            results = json.loads(result.stdout)
            published = 0
            expected = {p["id"]: thumbnail_name(p["id"], p["digest"]) for p in targets}
            for row in results:
                if row.get("status") != "ok" or row.get("filename") != expected.get(
                    row.get("id")
                ):
                    continue
                path = staging / row["filename"]
                if (
                    path.is_symlink()
                    or not path.is_file()
                    or not 100 < path.stat().st_size <= 2_000_000
                ):
                    continue
                data = path.read_bytes()
                if not data.startswith(b"\xff\xd8\xff") or not data.endswith(
                    b"\xff\xd9"
                ):
                    continue
                temporary = output / (row["filename"] + ".next")
                temporary.write_bytes(data)
                temporary.chmod(0o644)
                temporary.replace(output / row["filename"])
                published += 1
            print(str(published) + " miniature(s) publiée(s).")


if __name__ == "__main__":
    refresh()
