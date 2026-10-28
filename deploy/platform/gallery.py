#!/usr/bin/env python3
"""Galerie publique : noms explicitement autorisés, projets et aperçus ; aucun secret ni observation privée."""

import argparse
import html
import json
from pathlib import Path
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit

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

STYLE += ".project-menu{display:flex;flex-wrap:wrap;gap:16px;margin:12px 0}.project-menu a,.project-link{color:var(--accent)}.project-link{text-decoration:none}.project-menu a{padding:8px 0}.progress-item{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px;margin:16px 0;overflow-wrap:anywhere}.progress-item h3{margin-top:0}.status-label{font-weight:650;color:var(--accent)}summary{cursor:pointer;font-weight:600}a:focus-visible{outline:3px solid var(--focus);outline-offset:3px}code{overflow-wrap:anywhere}"

STYLE += ".automatic-evaluation{background:var(--subtle);border:2px solid var(--accent);border-radius:12px;padding:20px;margin:12px 0}.automatic-evaluation h2,.automatic-evaluation h3{margin-top:0}.automatic-count{display:block;font-size:20px;line-height:1.4;color:var(--accent)}.automatic-cta{display:block;margin-top:14px;padding:12px;border-radius:8px;background:var(--button-bg);color:var(--button-text);text-decoration:none;text-align:center;font-size:13px;font-weight:700}.automatic-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.automatic-grid>div{padding:12px;border:1px solid var(--border);border-radius:8px;background:var(--surface)}.automatic-grid strong{display:block;margin-top:8px;color:var(--accent);font-size:12px}"

# Vue de promotion compacte ; les fiches de progression gardent leur mise en page.
STYLE += """
.gallery-page header{padding:12px 28px;gap:12px}
.gallery-page main{max-width:1440px;padding:24px 28px}
.gallery-page h1{font-size:clamp(26px,3vw,34px);margin:8px 0}
.gallery-page .eyebrow{font-size:11px;margin:0 0 8px}
.gallery-page .intro{font-size:13px;line-height:1.5;max-width:780px;margin:8px 0 12px}
.gallery-page main>.automatic-evaluation{padding:12px 16px;border-width:1px;margin:12px 0}
.gallery-page main>.automatic-evaluation h2{font-size:18px;margin:0 0 6px}
.gallery-page main>.automatic-evaluation p{font-size:12px;line-height:1.5;margin:0}
.gallery-page .notice{padding:10px 14px;font-size:12px;line-height:1.5;margin:12px 0}
.gallery-page .grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}
.gallery-page .card{padding:14px;gap:8px;border-radius:10px;min-width:0}
.gallery-page .card h2{font-size:16px;line-height:1.3;flex:initial;overflow-wrap:anywhere}
.gallery-page .card small{font-size:11px}
.gallery-page .student-name{font-size:12px}
.gallery-page .card .automatic-evaluation{padding:10px;margin:0;border-width:1px;border-radius:8px}
.gallery-page .card .automatic-evaluation h3{font-size:13px;line-height:1.3;margin:0 0 5px}
.gallery-page .card .automatic-count{font-size:14px}
.gallery-page .automatic-cta{margin-top:8px;padding:8px;font-size:11px;border-radius:6px}
.gallery-page .project-preview,.gallery-page .preview-pending{aspect-ratio:2/1;border-radius:6px}
.gallery-page .commit-chart{margin:2px 0}
.gallery-page .commit-chart svg{height:32px;margin:3px 0}
.gallery-page .chart-empty{margin:4px 0}
.gallery-page .project-menu{gap:12px;margin:0}
.gallery-page .project-menu a{padding:6px 0;font-size:12px}
.gallery-page footer{padding:16px 28px;font-size:11px}
@media(max-width:1200px){.gallery-page .grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:900px){.gallery-page .grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:580px){.gallery-page header{padding:12px 16px}.gallery-page main{padding:20px 16px}.gallery-page .grid{grid-template-columns:minmax(0,1fr)}.gallery-page .automatic-cta{padding:10px}.gallery-page .project-preview,.gallery-page .preview-pending{aspect-ratio:2.2/1}}
"""

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
        if len(row["slug"]) > 100 or row["slug"] in used or row["id"] in identifiers or row["slug"] in {"progression", "previews"}:
            raise ValueError("Chemin trop long ou dupliqué.")
        used.add(row["slug"])
        identifiers.add(row["id"])
    return rows


def page(title, body, gallery=False):
    return (
        '<!doctype html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
        + html.escape(title)
        + '</title><meta name="color-scheme" content="light dark"><meta name="theme-color" content="#f6f7f2"><script>'
        + THEME_INIT
        + "</script><style>"
        + STYLE
        + '</style></head><body' + (' class="gallery-page"' if gallery else '') + '><header><span class="brand">i. IHME · Atelier de projets</span><button id="theme-toggle" class="theme-toggle" type="button" hidden aria-pressed="false" aria-label="Activer le mode nuit"><span id="theme-icon" class="theme-icon" aria-hidden="true">☾</span><span id="theme-label">Mode nuit</span></button></header><main>'
        + body
        + "</main><footer>Projets étudiants · Données réelles de la promotion</footer><script>"
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


def render_automatic_evaluation(report, identity, compact=False):
    report = report if isinstance(report, dict) else {}
    evaluation = report.get("evaluation") or {}
    available = evaluation.get("available", bool(report.get("generated_at")))
    entries = evaluation.get("milestones") or [
        {"title": m.get("title", ""), "observed": bool((m.get("automatic") or {}).get("observed"))}
        for m in report.get("milestones", [])
    ]
    observed = sum(bool(m.get("observed")) for m in entries)
    count = str(observed) + '/6 jalons avec indices' if available else 'Évaluation en attente'
    body = '<section class="automatic-evaluation"' + ('' if compact else ' id="evaluation-automatique"') + '><' + ('h3' if compact else 'h2') + '>Évaluation automatique</' + ('h3' if compact else 'h2') + '><strong class="automatic-count">' + count + '</strong>'
    if report.get("stale"):
        body += '<p>À actualiser</p>'
    if compact:
        return body + '<a class="automatic-cta" href="/progression/' + identity + '/#evaluation-automatique">Voir l’évaluation automatique →</a></section>'
    body += '<p>Diagnostic du dépôt : les indices sont à confirmer par une démonstration. La validation des compétences et la note sur 20 restent enseignantes.</p>'
    if available:
        strengths = [html.escape(str(m.get("title", ""))) for m in entries if m.get("observed")]
        body += '<h3>Points repérés automatiquement</h3><p>' + (' · '.join(strengths) if strengths else 'Aucun indice concluant dans l’échantillon lu ; à vérifier.') + '</p><h3>Priorités proposées</h3><ol>'
        for priority in evaluation.get("priorities", []):
            body += '<li>' + html.escape(str(priority)) + '</li>'
        body += '</ol><div class="automatic-grid">'
        for entry in entries:
            body += '<div>' + html.escape(str(entry.get("title", ""))) + '<strong>' + ('Indices repérés' if entry.get("observed") else 'À vérifier') + '</strong></div>'
        body += '</div>'
    else:
        body += '<p>Publier le travail dans le dépôt, puis demander une évaluation automatique.</p>'
    return body + '</section>'


def repository_link(project):
    """Lien de forge uniquement : aucun identifiant, jeton, paramètre ou hôte arbitraire."""
    value = project.get("repository", "")
    if not isinstance(value, str):
        return ""
    try:
        url = urlsplit(value)
        if (url.scheme != "https" or url.hostname not in {"github.com", "gitlab.com"}
                or url.username or url.password or url.port or url.query or url.fragment):
            return ""
    except ValueError:
        return ""
    parts = url.path.strip("/").split("/")
    if (len(parts) < 2 or (url.hostname == "github.com" and len(parts) != 2)
            or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) or part in {".", ".."} for part in parts)):
        return ""
    label = "GitHub" if url.hostname == "github.com" else "GitLab"
    return ('<a class="arrow repository-link" href="' + html.escape(value, quote=True)
            + '" target="_blank" rel="noopener noreferrer" aria-label="Voir le dépôt '
            + label + ' du projet ' + html.escape(project["id"].upper()) + '">'
            + label + ' ↗</a>')


def render_gallery(rows, activity=None, deployments=None, progression=None):
    deployments = deployments or {}
    activity = activity or {}
    progression = progression or {}
    checked_rows(rows)
    cards = []
    for r in rows:
        identity = "P" + str(int(r["id"][1:]))
        report = progression.get(r["id"])
        progress = ""
        if isinstance(report, dict):
            count = sum(m.get("status") == "done" for m in report.get("milestones", []))
            progress = '<small>' + str(count) + '/6 jalons validés par l’enseignant</small>'
        cards.append(
            '<article class="card"><small>' + identity + '</small><span class="student-name">'
            + html.escape(r.get("student_name", "")) + '</span><h2>'
            + html.escape(r["title"]) + '</h2>' + render_automatic_evaluation(report, r["id"], compact=True) + '<a class="project-link" href="/'
            + r["slug"] + '/" aria-label="Ouvrir le site du projet ' + identity + '">'
            + render_preview(r, deployments.get(r["id"])) + '</a>'
            + render_chart(activity.get(r["id"])) + progress
            + '<nav class="project-menu" aria-label="Menu du projet ' + identity + '">'
            + '<a class="arrow" href="/' + r["slug"] + '/">Site ↗</a>'
            + '<a class="arrow" href="/progression/' + r["id"] + '/">Progression →</a>'
            + repository_link(r) + '</nav></article>'
        )
    return page(
        "IHME — Les projets",
        '<p class="eyebrow">ATELIER REACT · EXPRESS · POSTGRESQL</p><h1>Les projets de la promotion</h1><p class="intro">Explorez les applications et consultez l’évaluation automatique de chaque projet, les attendus et les prochaines actions.</p><section class="automatic-evaluation"><h2>Évaluation automatique des projets</h2><p>Chaque carte affiche le diagnostic automatique des six jalons. Ouvrez « Voir l’évaluation automatique » pour consulter les points repérés et les priorités. Ce diagnostic ne constitue pas une note sur 20.</p></section><p class="notice">'
        + str(len(rows)) + ' espaces préparés. Un espace reste en attente tant que son application n’a pas été déployée par son auteur.</p><div class="grid">'
        + "".join(cards) + "</div>",
        gallery=True,
    )


def public_date(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y à %H:%M")
    except (ValueError, TypeError):
        return "Date non disponible"


def render_progress(project, report=None):
    checked_rows([project])
    escape = lambda value: html.escape(str("" if value is None else value), quote=True)
    identity = "P" + str(int(project["id"][1:]))
    intro = '<nav class="project-menu"><a href="/">← Tous les projets</a><a href="/' + project["slug"] + '/">Voir le site ↗</a></nav><p class="eyebrow">' + identity + ' · M2 IHME STAPS · 10 HEURES</p><h1>' + escape(project["title"]) + '</h1><p>' + escape(project.get("student_name", "")) + '</p><p class="notice">Progression formative publique. Un indice automatique n’est pas une compétence validée ni une note. Priorité : un scénario utile, un calcul expliqué et trois essais simples.</p>'
    if not isinstance(report, dict):
        return page(identity + " — Progression", intro + render_automatic_evaluation(None, project["id"]) + '<h2>Bilan à préparer</h2><p>La première analyse n’est pas encore disponible. Préparez un exemple normal, un cas vide et un cas limite, puis expliquez votre calcul et vos données à l’enseignant.</p>')
    milestones = report.get("milestones", [])
    validated = sum(m.get("status") == "done" for m in milestones)
    body = intro + render_automatic_evaluation(report, project["id"]) + '<h2>Validation enseignante des jalons</h2><p><strong>' + str(validated) + '/6 jalons validés</strong> par l’enseignant.</p>'
    if report.get("generated_at"):
        sha = str(report.get("sha", ""))
        ref = sha[:7] if re.fullmatch(r"[a-f0-9]{40,64}", sha) else "non disponible"
        body += '<p>Dernier bilan : ' + public_date(report["generated_at"]) + ' · Paris · commit <code>' + ref + '</code>. Lecture d’un échantillon de fichiers, sans exécution du code.</p>'
    else:
        body += '<p>Analyse automatique non encore disponible. Les validations enseignantes restent affichées.</p>'
    if report.get("empty"):
        body += '<p class="notice">Ce dépôt ne contient pas encore de commit. Publiez un premier commit, puis demandez une nouvelle analyse. Aucun zéro n’est attribué automatiquement.</p>'
    elif report.get("stale") or report.get("unavailable"):
        body += '<p class="notice">Analyse à actualiser ou accès au dépôt indisponible. Le dernier bilan réussi est conservé ; cela ne signifie pas que le travail est absent.</p>'
    body += '<nav class="project-menu" aria-label="Sections de la progression"><a href="#evaluation-automatique">Évaluation automatique</a><a href="#jalons">Jalons</a><a href="#revues">Revues</a><a href="#evaluation">Évaluation enseignante</a></nav><h2 id="jalons">Les jalons et les prochaines actions</h2>'
    labels = {"todo": "À faire · à vérifier", "doing": "En cours", "done": "Validé", "blocked": "Bloqué"}
    for m in milestones:
        status = m.get("status", "todo")
        auto = m.get("automatic") or {}
        body += '<article class="progress-item"><h3>' + escape(m.get("position")) + '. ' + escape(m.get("title")) + '</h3><p class="status-label">' + labels.get(status, labels["todo"]) + (' · décision enseignante' if m.get("teacher") else ' · proposition à confirmer') + '</p><p><strong>Attendu :</strong> ' + escape(m.get("expected")) + '</p><p><strong>À montrer :</strong> ' + escape(m.get("demonstration")) + '</p><p><strong>Indice automatique :</strong> ' + escape(auto.get("summary", "Non vérifié.")) + '</p>'
        if m.get("public_note"):
            body += '<p><strong>Retour enseignant :</strong> ' + escape(m["public_note"]) + '</p>'
        if status != "done":
            body += '<p><strong>Prochaine action :</strong> ' + escape(auto.get("next") or m.get("next")) + '</p>'
        body += '</article>'
    body += '<h2 id="revues">Journal des revues publiées</h2>'
    reviews = report.get("reviews", [])
    if not reviews:
        body += '<p>Aucune revue publiée pour le moment.</p>'
    for r in reviews:
        body += '<article class="progress-item"><h3>Revue du ' + escape(r.get("date")) + '</h3><p><strong>Acquis :</strong> ' + escape(r.get("achievements")) + '</p><p><strong>Prochaine étape :</strong> ' + escape(r.get("next_step")) + '</p></article>'
    body += '<details><summary>Historique des bilans automatiques</summary><p>Ces relevés ne sont pas des échanges avec l’enseignant.</p><ul>'
    for h in report.get("history", []):
        body += '<li>' + public_date(h.get("generated_at")) + ' · ' + escape(str(h.get("sha", ""))[:7]) + ' · ' + escape(h.get("observed")) + '/6 jalons avec indices</li>'
    body += '</ul></details><h2 id="evaluation">Évaluation enseignante facultative</h2><p>La grille est renseignée par l’enseignant après démonstration et explication. Une compétence non observée reste à vérifier ; aucun zéro n’est attribué automatiquement.</p>'
    assessment = report.get("assessment")
    criteria = report.get("criteria", [])
    scores = {s.get("key"): s.get("value") for s in assessment.get("scores", [])} if isinstance(assessment, dict) else {}
    complete = bool(assessment) and len(criteria) == 5
    total = 0
    for c in criteria:
        value = scores.get(c.get("key"))
        valid = type(value) in (int, float) and 0 <= value <= c.get("max", 0)
        complete = complete and valid
        if valid:
            total += value
        body += '<details class="progress-item"><summary>' + escape(c.get("title")) + ' · ' + (escape(value) if valid else 'À vérifier') + '/' + escape(c.get("max")) + '</summary><p>' + escape(c.get("anchors")) + '</p></details>'
    if complete:
        body += '<p><strong>Appréciation enseignante : ' + str(round(total, 2)) + '/20</strong></p>'
    else:
        body += '<p>Évaluation non publiée ou incomplète ; aucun total affiché.</p>'
    if isinstance(assessment, dict) and assessment.get("comment"):
        body += '<p>' + escape(assessment["comment"]) + '</p>'
    return page(identity + " — Progression", body)


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
    handle /progression/* {
        root * /srv/gallery
        header X-Content-Type-Options nosniff
        header Cache-Control "no-cache"
        file_server
    }
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
