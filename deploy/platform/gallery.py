#!/usr/bin/env python3
"""Génère uniquement la galerie publique ; ignore noms, mails, dépôts et jetons privés."""

import argparse
import html
import json
from pathlib import Path
import re

STYLE = """*{box-sizing:border-box}body{margin:0;background:#f6f7f2;color:#173530;font-family:system-ui,sans-serif}header{padding:24px 6vw;background:#fff;border-bottom:1px solid #dce3db;font-weight:750}main{max-width:1150px;margin:auto;padding:48px 6vw}h1{font-size:clamp(30px,5vw,48px);letter-spacing:-1px;margin:12px 0}p{line-height:1.6;color:#60716a}.intro{max-width:700px}.eyebrow{font-size:12px;letter-spacing:1.5px;color:#51725f}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin:32px 0}.card{display:flex;flex-direction:column;gap:12px;background:white;border:1px solid #dce3db;border-radius:12px;padding:24px;color:#173530;text-decoration:none}.card:hover{border-color:#67845a}.card:focus-visible{outline:3px solid #a1bf7c;outline-offset:3px}.card h2{font-size:20px;line-height:1.3;margin:0;flex:1}.card small{color:#70806e}.arrow{color:#235d4c;font-size:13px;font-weight:650}footer{padding:24px 6vw;border-top:1px solid #dce3db;font-size:12px;color:#60716a}.notice{padding:18px 22px;border-radius:10px;background:#eaf0e4}.back{display:inline-block;padding:12px 18px;background:#235d4c;color:white;text-decoration:none;border-radius:8px}"""


def checked_rows(rows):
    used = set()
    identifiers = set()
    for row in rows:
        if not re.fullmatch(r"p[0-9]{2}", row["id"]) or not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", row["slug"]
        ):
            raise ValueError("Identifiant ou chemin invalide.")
        if len(row["slug"]) > 100 or row["slug"] in used or row["id"] in identifiers:
            raise ValueError("Chemin trop long ou dupliqué.")
        used.add(row["slug"])
        identifiers.add(row["id"])
    return rows


def page(title, body):
    return (
        '<!doctype html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
        + html.escape(title)
        + "</title><style>"
        + STYLE
        + "</style></head><body><header>i. IHME · Atelier de projets</header><main>"
        + body
        + "</main><footer>Applications pédagogiques · Données fictives uniquement</footer></body></html>"
    )


def render_gallery(rows):
    checked_rows(rows)
    cards = "".join(
        '<a class="card" href="/'
        + r["slug"]
        + '/"><small>'
        + html.escape(r["id"].upper())
        + "</small><h2>"
        + html.escape(r["title"])
        + '</h2><span class="arrow">Accéder au projet ↗</span></a>'
        for r in rows
    )
    return page(
        "IHME — Les projets",
        '<p class="eyebrow">ATELIER REACT · EXPRESS · POSTGRESQL</p><h1>Les projets de la promotion</h1><p class="intro">Un espace de démonstration pour chaque projet. Explorez les applications au fil de leur publication.</p><p class="notice">'
        + str(len(rows))
        + ' espaces préparés. Un espace reste en attente tant que son application n’a pas été déployée par son auteur.</p><div class="grid">'
        + cards
        + "</div>",
    )


def render_caddy(teacher_host, student_host, rows):
    checked_rows(rows)
    for host in [teacher_host, student_host]:
        if not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}", host):
            raise ValueError("Nom d’hôte invalide.")
    if teacher_host == student_host:
        raise ValueError("Le carnet enseignant doit avoir une origine distincte.")
    pending = page(
        "IHME — Application en attente",
        '<p class="eyebrow">ESPACE PROJET</p><h1>Cette application n’est pas encore disponible.</h1><p>Son espace est préparé. Il attend son premier déploiement ou une remise en ligne par son auteur.</p><a class="back" href="/">← Revenir aux projets</a>',
    )
    routes = "".join(
        "    redir /"
        + r["slug"]
        + " /"
        + r["slug"]
        + "/ 308\n    handle_path /"
        + r["slug"]
        + "/* {\n        reverse_proxy "
        + r["id"]
        + ":3000\n    }\n"
        for r in rows
    )
    return (
        """{
    admin localhost:2019
}
"""
        + teacher_host
        + """ {
    encode zstd gzip
    reverse_proxy ihme-app:3000
}
"""
        + student_host
        + """ {
    encode zstd gzip
    handle /__deploy/* {
        request_body {
            max_size 4KB
        }
        reverse_proxy unix//run/ihme-deploy/http.sock
    }
"""
        + routes
        + """    handle {
        root * /srv/gallery
        rewrite * /index.html
        file_server
    }
    handle_errors {
        header Content-Type "text/html; charset=utf-8"
        respond `"""
        + pending
        + """` 503
    }
}
"""
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ["teacher-host", "student-host", "assignments", "gallery", "caddy"]:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    rows = json.loads(Path(args.assignments).read_text())
    Path(args.gallery).write_text(render_gallery(rows))
    Path(args.caddy).write_text(
        render_caddy(args.teacher_host, args.student_host, rows)
    )
