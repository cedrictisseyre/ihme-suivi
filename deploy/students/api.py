#!/usr/bin/env python3
"""API de déploiement privée sur socket Unix ; publiée uniquement derrière le proxy HTTPS."""

import hashlib
import hmac
import http.server
import json
from pathlib import Path
import re
import socketserver
import subprocess
import threading
import os

BASE = Path("/etc/ihme-students")
EXECUTABLE = "/usr/local/sbin/ihme-student-deploy"
TEACHER_BASE = Path("/etc/ihme-teacher")
TEACHER_EXECUTABLE = "/usr/local/sbin/ihme-teacher-deploy"
SOCKET = "/run/ihme-deploy/http.sock"
GATE = threading.Lock()
PUBLIC_ERRORS = {"configuration", "registry_auth", "image_pull", "unhealthy", "unhealthy_rollback"}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Ne pas journaliser les en-têtes ni les jetons.

    def reply(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        self.connection.settimeout(15)
        match = re.fullmatch(r"/__deploy/(p[0-9]{2}|suivi)", self.path)
        if not match:
            return self.reply(404, {"error": "Route inconnue."})
        project = match.group(1)
        token = self.headers.get("Authorization", "")
        try:
            folder = TEACHER_BASE if project == "suivi" else BASE / project
            expected = (folder / ".deploy-token.sha256").read_text().strip()
        except OSError:
            expected = "0" * 64
        if (
            not token.startswith("Bearer ")
            or len(token) > 200
            or not hmac.compare_digest(
                hashlib.sha256(token[7:].encode()).hexdigest(), expected
            )
        ):
            return self.reply(401, {"error": "Accès de déploiement refusé."})
        if self.headers.get("Transfer-Encoding"):
            return self.reply(400, {"error": "Content-Length requis."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                raise ValueError()
            data = json.loads(self.rfile.read(length))
            if (
                not isinstance(data, dict)
                or not {"digest"} <= set(data) <= {"digest", "registry_token"}
                or not isinstance(data["digest"], str)
            ):
                raise ValueError()
            registry_token = data.get("registry_token", "")
            if (
                not isinstance(registry_token, str)
                or len(registry_token) > 2048
                or any(ord(c) < 33 or ord(c) > 126 for c in registry_token)
            ):
                raise ValueError()
            digest = data["digest"]
            if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
                raise ValueError()
        except (ValueError, OSError):
            return self.reply(400, {"error": "Objet JSON avec digest SHA-256 attendu."})
        if not GATE.acquire(blocking=False):
            return self.reply(
                409,
                {"error": "Un déploiement est en cours. Réessayez dans une minute."},
            )
        try:
            command = (
                [TEACHER_EXECUTABLE] if project == "suivi" else [EXECUTABLE, project]
            )
            environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/root"}
            if registry_token:
                environment["IHME_REGISTRY_TOKEN"] = registry_token
            result = subprocess.run(
                command,
                input=digest + "\n",
                text=True,
                capture_output=True,
                timeout=450,
                env=environment,
            )
            if result.returncode:
                print(project + ": déploiement refusé ou non sain.", flush=True)
                code = result.stderr.strip().removeprefix("DEPLOY_ERROR:")
                if code not in PUBLIC_ERRORS:
                    code = "deployment_failed"
                return self.reply(
                    422,
                    {
                        "error": "Déploiement refusé ou version non saine. Consulter l’enseignant.",
                        "error_code": code
                    },
                )
            return self.reply(
                200, {"project": project, "status": "healthy", "digest": digest}
            )
        except subprocess.SubprocessError:
            return self.reply(
                503, {"error": "Déploiement indisponible. Consulter l’enseignant."}
            )
        finally:
            GATE.release()

    def do_GET(self):
        self.reply(405, {"error": "Utiliser POST avec le jeton personnel."})


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


if __name__ == "__main__":
    Path(SOCKET).parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    if Path(SOCKET).exists():
        Path(SOCKET).unlink()
    with Server(SOCKET, Handler) as server:
        os.chmod(SOCKET, 0o660)
        server.serve_forever()
