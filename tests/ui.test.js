import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let vite, CommitChart;
before(async () => {
  vite = await createServer({
    server: { middlewareMode: true, hmr: false, watch: null },
    appType: "custom",
    logLevel: "silent",
  });
  ({ default: CommitChart } = await vite.ssrLoadModule("/src/CommitChart.jsx"));
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
