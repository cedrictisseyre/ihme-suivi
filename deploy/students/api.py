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
SOCKET = "/run/ihme-deploy/http.sock"
GATE = threading.Lock()


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
        match = re.fullmatch(r"/__deploy/(p[0-9]{2})", self.path)
        if not match:
            return self.reply(404, {"error": "Route inconnue."})
        project = match.group(1)
        token = self.headers.get("Authorization", "")
        try:
            expected = (BASE / project / ".deploy-token.sha256").read_text().strip()
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
                or set(data) != {"digest"}
                or not isinstance(data["digest"], str)
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
            result = subprocess.run(
                [EXECUTABLE, project],
                input=digest + "\n",
                text=True,
                capture_output=True,
                timeout=450,
                env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/root"},
            )
            if result.returncode:
                print(project + ": déploiement refusé ou non sain.", flush=True)
                return self.reply(
                    422,
                    {
                        "error": "Déploiement refusé ou version non saine. Consulter l’enseignant."
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
