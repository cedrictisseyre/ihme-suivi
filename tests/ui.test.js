import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let vite, CommitChart, SitePreview, AutomaticEvaluation;
before(async () => {
  vite = await createServer({
    server: { middlewareMode: true, hmr: false, watch: null },
    appType: "custom",
    logLevel: "silent",
  });
  ({ default: CommitChart } = await vite.ssrLoadModule("/src/CommitChart.jsx"));
  ({ default: SitePreview } = await vite.ssrLoadModule("/src/SitePreview.jsx"));
  ({ default: AutomaticEvaluation } = await vite.ssrLoadModule(
    "/src/AutomaticEvaluation.jsx",
  ));
});
after(async () => {
  await vite?.close();
});

test("le graphique se rend avec la transformation JSX réelle de Vite", () => {
  const days = Array.from({ length: 14 }, (_, i) => ({
    date: `2026-10-${i + 13}`,
    count: i === 13 ? 3 : 0,
  }));
  const html = renderToStaticMarkup(
    React.createElement(CommitChart, { activity: { days, complete: true } }),
  );
  assert.equal((html.match(/<rect /g) || []).length, 14);
  assert.match(html, /3 commits/);
  assert.match(html, /<title>26\/10 : 3 commits<\/title>/);
  assert.match(html, /26\/10/);
  assert.match(html, /role="img"/);
});
test("la fiche reste affichable avant la première lecture Git", () => {
  const html = renderToStaticMarkup(
    React.createElement(CommitChart, { activity: null }),
  );
  assert.match(html, /données à actualiser/);
});

test("aperçu étudiant : lien accessible et état sans miniature", () => {
  const p = {
    student_name: "Étudiant",
    site: {
      url: "https://example.org/site/",
      thumbnail: "/api/project-previews/image.jpg",
    },
  };
  const html = renderToStaticMarkup(React.createElement(SitePreview, { p }));
  assert.match(html, /Aperçu du site de Étudiant/);
  assert.match(html, /href="https:\/\/example.org\/site\/"/);
  assert.match(html, /loading="lazy"/);
  const pending = renderToStaticMarkup(
    React.createElement(SitePreview, {
      p: { ...p, site: { url: p.site.url } },
    }),
  );
  assert.match(pending, /Miniature à venir/);
  assert.match(pending, /Voir le site/);
  const missing = renderToStaticMarkup(
    React.createElement(SitePreview, { p: {} }),
  );
  assert.match(missing, /Site à renseigner/);
});

test("évaluation automatique visible sur la carte et diagnostic détaillé sans note inventée", async () => {
  const { automaticEvaluation } =
    await import("../server/automatic-evaluation.js");
  const evaluation = automaticEvaluation({
    milestones: [{ position: 2, observed: true }],
  });
  assert.equal(evaluation.observed, 1);
  assert.equal(evaluation.total, 6);
  assert.equal(evaluation.milestones.length, 6);
  assert.equal(evaluation.priorities.length, 3);
  assert.equal(evaluation.score, undefined);
  const p = { student_name: "Démo", progression: { evaluation } };
  const card = renderToStaticMarkup(
    React.createElement(AutomaticEvaluation, { p, compact: true }),
  );
  assert.match(card, /ÉVALUATION AUTOMATIQUE/);
  assert.match(card, /1\/6 jalons avec indices/);
  assert.match(card, /Voir l’évaluation automatique/);
  const detail = renderToStaticMarkup(
    React.createElement(AutomaticEvaluation, { p }),
  );
  assert.match(detail, /Priorités proposées/);
  assert.match(detail, /Indices repérés/);
  assert.match(detail, /À vérifier/);
  const pending = renderToStaticMarkup(
    React.createElement(AutomaticEvaluation, { p: {} }),
  );
  assert.match(pending, /Évaluation en attente/);
  assert.doesNotMatch(pending, /0\/6/);
});
