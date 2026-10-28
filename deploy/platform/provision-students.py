#!/usr/bin/env python3
import os, json, hashlib, secrets, subprocess, shutil, argparse, re
from gallery import checked_rows, render_caddy, render_gallery, render_pending
from pathlib import Path

os.umask(0o077)
parser = argparse.ArgumentParser(
    description="Provisionnement administratif des espaces étudiants ; entrée privée non versionnée."
)
parser.add_argument("--assignments", required=True)
parser.add_argument("--teacher-host", required=True)
parser.add_argument("--student-host", required=True)
args = parser.parse_args()
if os.geteuid() != 0:
    raise ValueError("Administration root requise.")
rows = checked_rows(json.loads(Path(args.assignments).read_text()))
render_caddy(args.teacher_host, args.student_host, rows)
for row in rows:
    if not re.fullmatch(
        r"[a-z0-9][a-z0-9._/-]{1,250}", row["image_repository"]
    ) or not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", row["token"]):
        raise ValueError("Dépôt d’image ou jeton invalide.")
root = Path("/opt/ihme-suivi")
platform = root / "deploy/platform"
etc = Path("/etc/ihme-students")
etc.mkdir(exist_ok=True, mode=0o700)
installed = Path("/opt/ihme-platform")
installed.mkdir(exist_ok=True, mode=0o755)
for src, dst in [
    ("deploy.py", "/usr/local/sbin/ihme-student-deploy"),
    ("api.py", str(installed / "deploy-api.py")),
    ("compose.student.yaml", str(installed / "compose.student.yaml")),
]:
    shutil.copyfile(root / "deploy/students" / src, dst)
    os.chmod(dst, 0o755 if src == "deploy.py" else 0o600)
shutil.copyfile(
    root / "deploy/students/ihme-deploy.service",
    "/etc/systemd/system/ihme-deploy.service",
)


def run(*args, input=None):
    return subprocess.run(
        args, input=input, text=True, check=True, capture_output=True
    ).stdout


shutil.copyfile(platform / "compose.yaml", installed / "compose.yaml")
networks = {}
services = {"db": {"networks": {"database": {}}}, "proxy": {"networks": {"web": {}}}}
sql = ""
hba = "local all all trust\nhost ihme_suivi ihme_suivi 0.0.0.0/0 scram-sha-256\n"
routes = []
for n, a in enumerate(rows, 1):
    project = a["id"]
    folder = etc / project
    folder.mkdir(exist_ok=True, mode=0o700)
    dbnet = "ihme-" + project + "-db"
    webnet = "ihme-" + project + "-web"
    for name, subnet in [(dbnet, f"172.29.{n}.0/28"), (webnet, f"172.29.{n}.16/28")]:
        if subprocess.run(
            ["docker", "network", "inspect", name], capture_output=True
        ).returncode:
            run("docker", "network", "create", "--subnet", subnet, name)
        networks[project + ("-db" if name == dbnet else "-web")] = {
            "external": True,
            "name": name,
        }
    services["db"]["networks"][project + "-db"] = {"aliases": ["postgres-" + project]}
    services["proxy"]["networks"][project + "-web"] = {}
    password = secrets.token_urlsafe(30)
    jwt_secret = secrets.token_urlsafe(48)
    config = folder / ".env.student"
    if config.exists():
        previous_config = dict(
            line.split("=", 1)
            for line in config.read_text().splitlines()
            if "=" in line and not line.startswith("#")
        )
        jwt_secret = previous_config.get("JWT_SECRET") or jwt_secret
        password = (
            config.read_text()
            .split("DATABASE_URL=postgresql://ihme_" + project + ":")[1]
            .split("@")[0]
        )
    config.write_text(
        "STUDENT_ID="
        + project
        + "\nSTUDENT_IMAGE_REPOSITORY="
        + a["image_repository"]
        + "\nDATABASE_URL=postgresql://ihme_"
        + project
        + ":"
        + password
        + "@postgres-"
        + project
        + ":5432/ihme_"
        + project
        + "\nPUBLIC_ORIGIN=https://"
        + args.student_host
        + "\nJWT_SECRET="
        + jwt_secret
        + "\nBASE_PATH=/"
        + a["slug"]
        + "/\nDB_NETWORK="
        + dbnet
        + "\nPROXY_NETWORK="
        + webnet
        + "\n"
    )
    (folder / ".deploy-token.sha256").write_text(
        hashlib.sha256(a["token"].encode()).hexdigest() + "\n"
    )
    sql += f"SELECT 'CREATE ROLE ihme_{project} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE CONNECTION LIMIT 4' WHERE NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='ihme_{project}')\\gexec\n"
    sql += f"ALTER ROLE ihme_{project} PASSWORD '{password}'; ALTER ROLE ihme_{project} SET statement_timeout='10s'; ALTER ROLE ihme_{project} SET idle_in_transaction_session_timeout='15s'; ALTER ROLE ihme_{project} SET work_mem='2MB';\n"
    sql += f"SELECT 'CREATE DATABASE ihme_{project} OWNER ihme_{project}' WHERE NOT EXISTS(SELECT 1 FROM pg_database WHERE datname='ihme_{project}')\\gexec\nREVOKE ALL ON DATABASE ihme_{project} FROM PUBLIC; GRANT CONNECT ON DATABASE ihme_{project} TO ihme_{project};\n\\connect ihme_{project}\nREVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE,CREATE ON SCHEMA public TO ihme_{project};\n\\connect postgres\n"
    hba += f"host ihme_{project} ihme_{project} 172.29.{n}.0/28 scram-sha-256\n"
    routes.append(
        f'    redir /{a["slug"]} /{a["slug"]}/ 308\n    handle_path /{a["slug"]}/* {{\n        reverse_proxy {project}:3000\n    }}\n'
    )
hba += "host all all 0.0.0.0/0 reject\nhost all all ::/0 reject\n"
# JSON est un format Compose valide ; aucun secret dans le manifeste de réseaux.
(installed / "compose.students.networks.json").write_text(
    json.dumps({"services": services, "networks": networks}, indent=2)
)
base = [
    "docker",
    "compose",
    "--project-name",
    "ihme-platform",
    "--env-file",
    str(installed / ".env.platform"),
    "-f",
    str(installed / "compose.yaml"),
    "-f",
    str(installed / "compose.students.networks.json"),
]
run(*base, "up", "-d", "db")
import time

for _ in range(30):
    if (
        subprocess.run(
            [
                "docker",
                "exec",
                "ihme-platform-db-1",
                "pg_isready",
                "-U",
                "platform_admin",
                "-d",
                "postgres",
            ],
            capture_output=True,
        ).returncode
        == 0
    ):
        break
    time.sleep(1)
run(
    "docker",
    "exec",
    "-i",
    "ihme-platform-db-1",
    "psql",
    "-U",
    "platform_admin",
    "-d",
    "postgres",
    "-v",
    "ON_ERROR_STOP=1",
    input=sql,
)
run(
    "docker",
    "exec",
    "-i",
    "ihme-platform-db-1",
    "sh",
    "-c",
    "cat > /var/lib/postgresql/data/pg_hba.conf",
    input=hba,
)
run(
    "docker",
    "exec",
    "ihme-platform-db-1",
    "psql",
    "-U",
    "platform_admin",
    "-d",
    "postgres",
    "-c",
    "SELECT pg_reload_conf();",
)
public = installed / "public"
public.mkdir(mode=0o755, exist_ok=True)
(public / "index.html").write_text(render_gallery(rows))
(public / "_unavailable.html").write_text(render_pending())
os.chmod(public / "_unavailable.html", 0o644)
os.chmod(public / "index.html", 0o644)
gallery_config = Path("/etc/ihme-gallery")
gallery_config.mkdir(mode=0o700, exist_ok=True)
(gallery_config / "projects.json").write_text(
    json.dumps(
        [
            {k: r[k] for k in ["id", "title", "slug", "repository"] if k in r}
            for r in rows
        ]
    )
)
(installed / "Caddyfile").write_text(
    render_caddy(args.teacher_host, args.student_host, rows)
)
# Config proxy : galerie publique statique, montée séparément de tout secret.
# Le manifeste initial est complété via un override de volumes.
services["proxy"]["volumes"] = [str(installed / "public") + ":/srv/gallery:ro"]
(installed / "compose.students.networks.json").write_text(
    json.dumps({"services": services, "networks": networks}, indent=2)
)
run("systemctl", "daemon-reload")
run("systemctl", "enable", "ihme-deploy.service")
run("systemctl", "restart", "ihme-deploy.service")
run(*base, "up", "-d", "proxy")
print(
    "20 bases/rôles isolés et accès HTTPS individuels préparés ; aucune application étudiante démarrée."
)
