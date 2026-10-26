import { test } from "node:test";
import assert from "node:assert/strict";
import { repositoryAddress, getActivity } from "../server/git.js";
test("URL Git strictes : pas de SSRF, identifiant ou autre hôte", () => {
  for (const url of [
    "http://github.com/a/b",
    "https://github.com.evil/a/b",
    "https://localhost/a/b",
    "https://user:pass@github.com/a/b",
    "https://github.com/a/b/issues",
    "https://github.com/a/b?token=x",
  ])
    assert.throws(() => repositoryAddress(url));
  assert.equal(
    repositoryAddress("https://github.com/demo/projet.git").path,
    "demo/projet",
  );
  assert.equal(
    repositoryAddress("https://gitlab.com/groupe/sous-groupe/projet").path,
    "groupe/sous-groupe/projet",
  );
});
test("activité GitHub : pagination, jeton serveur, minimisation des données", async () => {
  const data = await getActivity("https://github.com/demo/projet", {
    page: 2,
    githubToken: "test-only",
    fetcher: async (url, options) => {
      assert.match(url, /page=2/);
      assert.equal(options.headers.Authorization, "Bearer test-only");
      assert.equal(options.redirect, "error");
      return {
        ok: true,
        json: async () => [
          {
            sha: "a".repeat(40),
            commit: {
              message: "Test\nDétail",
              committer: {
                date: "2026-10-26T10:00:00Z",
                email: "private@example.test",
              },
            },
          },
        ],
      };
    },
  });
  assert.equal(data.commits[0].title, "Test");
  assert.ok(!JSON.stringify(data).includes("email"));
  assert.ok(!JSON.stringify(data).includes("test-only"));
});
test("erreurs Git privées et quota restent explicites sans exposer de secret", async () => {
  await assert.rejects(
    () =>
      getActivity("https://github.com/demo/projet", {
        fetcher: async () => ({ ok: false, status: 404 }),
      }),
    /privé/,
  );
  await assert.rejects(
    () =>
      getActivity("https://github.com/demo/projet", {
        fetcher: async () => ({ ok: false, status: 429 }),
      }),
    /Quota/,
  );
});
test("dépôt GitHub vide distinct d’un dépôt inaccessible", async () => {
  const activity = await getActivity("https://github.com/demo/vide", {
    fetcher: async () => ({ ok: false, status: 409 }),
  });
  assert.deepEqual(activity.commits, []);
  assert.equal(activity.hasNext, false);
});

test("comptes journaliers : 14 jours, Paris, changement d’heure, dédoublonnage et zéros", async () => {
  const { dailyCounts } = await import("../server/git.js");
  const days = dailyCounts(
    [
      { sha: "a", date: "2026-10-25T00:30:00Z" },
      { sha: "b", date: "2026-10-25T01:30:00Z" },
      { sha: "c", date: "2026-10-25T23:30:00Z" },
      { sha: "c", date: "2026-10-25T23:30:00Z" },
      { sha: "old", date: "2026-10-01T12:00:00Z" },
      { sha: "invalid", date: "invalid" },
    ],
    new Date("2026-10-26T12:00:00Z"),
  );
  assert.equal(days.length, 14);
  assert.equal(days[0].date, "2026-10-13");
  assert.equal(days.at(-1).date, "2026-10-26");
  assert.equal(days.find((d) => d.date === "2026-10-25").count, 2);
  assert.equal(days.at(-1).count, 1);
  assert.equal(days[0].count, 0);
});
test("histogramme : pagination complète et dernier commit ancien conservé", async () => {
  const { getCommitSummary } = await import("../server/git.js");
  const fake = (i) => ({
    sha: String(i).padStart(40, "0"),
    commit: { message: "Démo", committer: { date: "2026-10-26T10:00:00Z" } },
  });
  const result = await getCommitSummary("https://github.com/demo/projet", {
    now: new Date("2026-10-26T12:00:00Z"),
    fetcher: async (url) => ({
      ok: true,
      json: async () =>
        new URL(url).searchParams.get("page") === "1"
          ? Array.from({ length: 100 }, (_, i) => fake(i))
          : [fake(100)],
    }),
  });
  assert.equal(result.activity.days.at(-1).count, 101);
  assert.equal(result.activity.complete, true);
  const old = await getCommitSummary("https://github.com/demo/projet", {
    now: new Date("2026-10-26T12:00:00Z"),
    fetcher: async (url) => ({
      ok: true,
      json: async () =>
        url.includes("since=")
          ? []
          : [
              {
                sha: "a".repeat(40),
                commit: {
                  message: "Ancien",
                  committer: { date: "2026-10-01T12:00:00Z" },
                },
              },
            ],
    }),
  });
  assert.equal(old.last.title, "Ancien");
  assert.equal(
    old.activity.days.reduce((s, d) => s + d.count, 0),
    0,
  );
});
test("histogramme : une collecte plafonnée est explicitement partielle", async () => {
  const { getCommitSummary } = await import("../server/git.js");
  let calls = 0;
  const result = await getCommitSummary("https://github.com/demo/projet", {
    now: new Date("2026-10-26T12:00:00Z"),
    fetcher: async () => {
      const page = calls++;
      return {
        ok: true,
        json: async () =>
          Array.from({ length: 100 }, (_, i) => ({
            sha: `${page}-${i}`,
            commit: {
              message: "Démo",
              committer: { date: "2026-10-26T10:00:00Z" },
            },
          })),
      };
    },
  });
  assert.equal(calls, 10);
  assert.equal(result.activity.complete, false);
  assert.equal(result.activity.days.at(-1).count, 1000);
});
