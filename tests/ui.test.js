import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let vite, CommitChart, SitePreview;
before(async () => {
  vite = await createServer({
    server: { middlewareMode: true, hmr: false, watch: null },
    appType: "custom",
    logLevel: "silent",
  });
  ({ default: CommitChart } = await vite.ssrLoadModule("/src/CommitChart.jsx"));
  ({ default: SitePreview } = await vite.ssrLoadModule("/src/SitePreview.jsx"));
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
