#!/usr/bin/env python3
"""Galerie publique : noms explicitement autorisés, projets et aperçus ; aucun secret ni observation."""

import argparse
import html
import json
from pathlib import Path
import re

LIGHT_PALETTE = "color-scheme:light;--bg:#f6f7f2;--surface:#fff;--text:#173530;--muted:#60716a;--eyebrow:#51725f;--border:#dce3db;--hover:#67845a;--focus:#a1bf7c;--accent:#235d4c;--subtle:#eaf0e4;--button-bg:#235d4c;--button-text:#fff;--caption:#355b46;--chart-bar:#6f9460;--chart-zero:#d4ddcf;"
DARK_PALETTE = "color-scheme:dark;--bg:#101914;--surface:#19271e;--text:#e5eee4;--muted:#b1c2b3;--eyebrow:#b5cc9f;--border:#35483a;--hover:#8cad77;--focus:#bcdb9a;--accent:#c3dfad;--subtle:#233529;--button-bg:#bcdb9a;--button-text:#142014;--caption:#b7ceb6;--chart-bar:#a0c886;--chart-zero:#3c5141;"
STYLE = (
    ":root{"
    + LIGHT_PALETTE
    + "}:root[data-theme=dark]{"
    + DARK_PALETTE
    + "}@media(prefers-color-scheme:dark){:root:not([data-theme]){"
    + DARK_PALETTE
    + "}}"
)
STYLE += ".student-name{font-size:13px;font-weight:650;color:var(--text)}.deployment-status{font-size:11px;color:var(--accent)}.project-preview{display:block;width:100%;height:auto;aspect-ratio:16/10;object-fit:cover;object-position:top;border:1px solid var(--border);border-radius:8px;background:var(--subtle)}.preview-pending{display:flex;align-items:center;justify-content:center;aspect-ratio:16/10;border-radius:8px;background:var(--subtle);color:var(--muted);font-size:12px}"
STYLE += """*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,sans-serif}header{padding:20px 6vw;background:var(--surface);border-bottom:1px solid var(--border);font-weight:750;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}.brand{font-size:15px}.theme-toggle{display:inline-flex;align-items:center;gap:8px;margin-left:auto;padding:9px 13px;border:1px solid var(--border);border-radius:9px;background:var(--surface);color:var(--text);font:inherit;font-size:13px;font-weight:600;cursor:pointer}.theme-toggle[hidden]{display:none}.theme-toggle:hover{background:var(--subtle)}.theme-toggle:focus-visible{outline:3px solid var(--focus);outline-offset:3px}.theme-icon{font-size:18px;line-height:1}main{max-width:1150px;margin:auto;padding:48px 6vw}h1{font-size:clamp(30px,5vw,48px);letter-spacing:-1px;margin:12px 0}p{line-height:1.6;color:var(--muted)}.intro{max-width:700px}.eyebrow{font-size:12px;letter-spacing:1.5px;color:var(--eyebrow)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin:32px 0}.card{display:flex;flex-direction:column;gap:12px;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;color:var(--text);text-decoration:none}.card:hover{border-color:var(--hover)}.card:focus-visible{outline:3px solid var(--focus);outline-offset:3px}.card h2{font-size:18px;line-height:1.3;margin:0;flex:1}.card small{color:var(--muted)}.arrow{color:var(--accent);font-size:13px;font-weight:650}footer{padding:24px 6vw;border-top:1px solid var(--border);font-size:12px;color:var(--muted)}.notice{padding:18px 22px;border-radius:10px;background:var(--subtle)}.back{display:inline-block;padding:12px 18px;background:var(--button-bg);color:var(--button-text);text-decoration:none;border-radius:8px}.commit-chart{display:block;margin:8px 0}.commit-chart svg{display:block;width:100%;height:45px;margin:5px 0}.chart-caption{display:flex;justify-content:space-between;font-size:11px;color:var(--caption)}.chart-axis,.chart-empty{font-size:10px;color:var(--muted)}.chart-empty{display:block;margin:10px 0}.chart-bar{fill:var(--chart-bar)}.chart-zero{fill:var(--chart-zero)}"""

THEME_INIT = """(function(){
  var stored=null;
  try{stored=window.localStorage.getItem('ihme-gallery-theme');}catch(error){}
  var dark=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches;
  var theme=stored==='light'||stored==='dark'?stored:dark?'dark':'light';
  document.documentElement.dataset.theme=theme;
  document.querySelector('meta[name="theme-color"]').setAttribute('content',theme==='dark'?'#101914':'#f6f7f2');
})();"""
THEME_CONTROL = """(function(){
  var key='ihme-gallery-theme';
  var button=document.getElementById('theme-toggle');
  var label=document.getElementById('theme-label');
  var icon=document.getElementById('theme-icon');
  var media=window.matchMedia?window.matchMedia('(prefers-color-scheme: dark)'):null;
  var explicit=false;
  try{var saved=window.localStorage.getItem(key);explicit=saved==='light'||saved==='dark';}catch(error){}
  function apply(theme){
    var dark=theme==='dark';
    document.documentElement.dataset.theme=theme;
    label.textContent=dark?'Mode jour':'Mode nuit';
    icon.textContent=dark?'☀':'☾';
    button.setAttribute('aria-pressed',String(dark));
    button.setAttribute('aria-label',dark?'Activer le mode jour':'Activer le mode nuit');
    document.querySelector('meta[name="theme-color"]').setAttribute('content',dark?'#101914':'#f6f7f2');
  }
  apply(document.documentElement.dataset.theme);
  button.hidden=false;
  button.addEventListener('click',function(){
    var theme=document.documentElement.dataset.theme==='dark'?'light':'dark';
    explicit=true;apply(theme);
    try{window.localStorage.setItem(key,theme);}catch(error){}
  });
  if(media&&media.addEventListener)media.addEventListener('change',function(event){if(!explicit)apply(event.matches?'dark':'light');});
  window.addEventListener('storage',function(event){
    if(event.key!==key)return;
    explicit=event.newValue==='dark'||event.newValue==='light';
    apply(explicit?event.newValue:media&&media.matches?'dark':'light');
  });
})();"""


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
        + '</title><meta name="color-scheme" content="light dark"><meta name="theme-color" content="#f6f7f2"><script>'
        + THEME_INIT
        + "</script><style>"
        + STYLE
        + '</style></head><body><header><span class="brand">i. IHME · Atelier de projets</span><button id="theme-toggle" class="theme-toggle" type="button" hidden aria-pressed="false" aria-label="Activer le mode nuit"><span id="theme-icon" class="theme-icon" aria-hidden="true">☾</span><span id="theme-label">Mode nuit</span></button></header><main>'
        + body
        + "</main><footer>Applications pédagogiques · Données fictives uniquement</footer><script>"
        + THEME_CONTROL
        + "</script></body></html>"
    )


def render_chart(activity):
    if not isinstance(activity, dict):
        return (
            '<span class="chart-empty">Commits par jour · données indisponibles</span>'
        )
    days = activity.get("days")
    if (
        not isinstance(days, list)
        or len(days) != 14
        or any(
            not isinstance(d, dict)
            or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", str(d.get("date", "")))
            or type(d.get("count")) is not int
            or not 0 <= d["count"] <= 1000000
            for d in days
        )
    ):
        return (
            '<span class="chart-empty">Commits par jour · données indisponibles</span>'
        )
    peak = max(d["count"] for d in days)
    total = sum(d["count"] for d in days)
    partial = not activity.get("complete", False)
    bars = []
    for i, d in enumerate(days):
        height = max(3, d["count"] / max(1, peak) * 40) if d["count"] else 1
        label = (
            d["date"][8:10]
            + "/"
            + d["date"][5:7]
            + " : "
            + str(d["count"])
            + " commits"
        )
        bars.append(
            f'<rect x="{i*20+2}" y="{44-height:.2f}" width="15" height="{height:.2f}" rx="2" class="{ "chart-bar" if d["count"] else "chart-zero" }"><title>{label}</title></rect>'
        )
    label = "Commits par jour, heure de Paris : " + ", ".join(
        d["date"] + " : " + str(d["count"]) for d in days
    )
    dates = (
        days[0]["date"][8:10]
        + "/"
        + days[0]["date"][5:7]
        + " — "
        + days[-1]["date"][8:10]
        + "/"
        + days[-1]["date"][5:7]
    )
    status = (
        " · dernière lecture disponible"
        if activity.get("stale")
        else " · lecture partielle" if partial else ""
    )
    return (
        '<span class="commit-chart"><span class="chart-caption"><span>'
        + ("≥ " if partial else "")
        + str(total)
        + " commits · 14 jours</span><span>max. "
        + str(peak)
        + '/j</span></span><svg viewBox="0 0 280 45" preserveAspectRatio="none" role="img" aria-label="'
        + html.escape(label, quote=True)
        + '">'
        + "".join(bars)
        + '</svg><span class="chart-axis">'
        + dates
        + " · Paris"
        + status
        + "</span></span>"
    )


def render_preview(project, deployment):
    if not deployment or not deployment.get("published"):
        return '<span class="deployment-status">À déployer</span>'
    status = (
        "En ligne" if deployment.get("available") else "Déjà déployé · indisponible"
    )
    image = deployment.get("thumbnail", "")
    if re.fullmatch(r"/previews/" + project["id"] + r"-[a-f0-9]{64}\.jpg", image):
        preview = (
            '<img class="project-preview" src="'
            + image
            + '" alt="Aperçu de '
            + html.escape(project["title"], quote=True)
            + '" width="1280" height="800" loading="lazy" decoding="async">'
        )
    else:
        preview = '<span class="preview-pending">Aperçu en préparation</span>'
    return '<span class="deployment-status">' + status + "</span>" + preview


def render_gallery(rows, activity=None, deployments=None):
    deployments = deployments or {}
    activity = activity or {}
    checked_rows(rows)
    cards = "".join(
        '<a class="card" href="/'
        + r["slug"]
        + '/"><small>'
        + html.escape(r["id"].upper())
        + '</small><span class="student-name">'
        + html.escape(r.get("student_name", ""))
        + "</span><h2>"
        + html.escape(r["title"])
        + "</h2>"
        + render_preview(r, deployments.get(r["id"]))
        + render_chart(activity.get(r["id"]))
        + '<span class="arrow">Accéder au projet ↗</span></a>'
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


def render_pending():
    return page(
        "IHME — Application en attente",
        '<p class="eyebrow">ESPACE PROJET</p><h1>Cette application n’est pas encore disponible.</h1><p>Son espace est préparé. Il attend son premier déploiement ou une remise en ligne par son auteur.</p><a class="back" href="/">← Revenir aux projets</a>',
    )


def render_caddy(teacher_host, student_host, rows):
    checked_rows(rows)
    for host in [teacher_host, student_host]:
        if not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}", host):
            raise ValueError("Nom d’hôte invalide.")
    if teacher_host == student_host:
        raise ValueError("Le carnet enseignant doit avoir une origine distincte.")
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
    handle /previews/* {
        root * /srv/gallery
        header X-Content-Type-Options nosniff
        file_server
    }
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
        root * /srv/gallery
        rewrite * /_unavailable.html
        file_server {
            status 503
        }
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
    (Path(args.gallery).parent / "_unavailable.html").write_text(render_pending())
    Path(args.caddy).write_text(
        render_caddy(args.teacher_host, args.student_host, rows)
    )
