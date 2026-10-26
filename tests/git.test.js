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
