import { test } from "node:test";
import assert from "node:assert/strict";
import request from "supertest";
import { PGlite } from "@electric-sql/pglite";
import { migrate } from "../server/db.js";
import { createApp } from "../server/app.js";
import {
  analyzeEvidence,
  readRepositoryEvidence,
} from "../server/analyze-progress.js";
import { publicProgress, exportProgress } from "../server/progression.js";
import { RUBRIC, ASSESSMENT_GUIDE } from "../server/rubric.js";

const sha = "a".repeat(40);
const repository = "https://github.com/demo/projet";
const sample = [
  {
    path: "README.md",
    content:
      "Un utilisateur STAPS veut calculer une durée moyenne à partir de séances fictives. ".repeat(
        3,
      ) +
      "\nnpm install\nCas normal, cas vide et cas limite : résultat attendu.",
  },
  {
    path: "schema.sql",
    content: "CREATE TABLE sessions(id INTEGER PRIMARY KEY, duration INTEGER);",
  },
  {
    path: "server/index.js",
    content:
      "const durations = values.filter(v => v > 0); if (durations.length) return durations.reduce((a,b)=>a+b,0)/durations.length; // PRIVATE_SOURCE",
  },
  {
    path: "src/App.jsx",
    content: "return <form><input /><button>Calculer</button></form>;",
  },
  {
    path: "tests/calculate.test.js",
    content: "test('normal', () => assert.equal(average([10,20]),15));",
  },
];

test("grille 10 h : indices explicites, jamais de jalon validé ni de note automatique", () => {
  assert.equal(RUBRIC.length, 6);
  assert.equal(
    ASSESSMENT_GUIDE.reduce((n, c) => n + c.max, 0),
    20,
  );
  const report = analyzeEvidence(sample, { sha, repository });
  assert.ok(report.milestones.every((m) => m.observed && m.status === "doing"));
  assert.ok(!JSON.stringify(report).includes("PRIVATE_SOURCE"));
  assert.equal(report.assessment, undefined);
  const empty = analyzeEvidence([], { sha, partial: true, repository });
  assert.ok(empty.milestones.every((m) => m.status === "todo" && !m.observed));
  assert.ok(empty.milestones.every((m) => /à vérifier/.test(m.summary)));
});

function fixtureFetch({ fail = false } = {}) {
  return async (url, options) => {
    assert.equal(options.redirect, "error");
    assert.equal(new URL(url).hostname, "api.github.com");
    if (fail) return new Response("private error", { status: 403 });
    if (url.includes("/commits?"))
      return Response.json([
        {
          sha,
          commit: {
            message: "demo",
            committer: { date: "2026-10-27T12:00:00Z" },
          },
        },
      ]);
    if (url.includes("/git/trees/")) {
      assert.ok(url.includes(sha));
      return Response.json({
        truncated: false,
        tree: sample
          .map((f, i) => ({
            path: f.path,
            type: "blob",
            mode: "100644",
            size: f.content.length,
            sha: String(i + 1).repeat(40),
            url: "https://evil.example/steal",
          }))
          .concat([
            {
              path: ".env",
              type: "blob",
              mode: "100644",
              size: 12,
              sha: "9".repeat(40),
            },
            {
              path: "README-secret.md",
              type: "blob",
              mode: "120000",
              sha: "8".repeat(40),
            },
          ]),
      });
    }
    const i = Number(url.split("/").at(-1)[0]) - 1;
    assert.ok(i >= 0 && i < sample.length);
    return Response.json({
      encoding: "base64",
      content: Buffer.from(sample[i].content).toString("base64"),
    });
  };
}

test("lecture Git épinglée au commit, URLs reconstruites, liens symboliques et secrets exclus", async () => {
  const report = await readRepositoryEvidence(repository, sha, {
    gitFetch: fixtureFetch(),
    githubToken: "fixture-private-token",
  });
  assert.ok(report.milestones.every((m) => m.observed));
  assert.ok(!JSON.stringify(report).includes("fixture-private-token"));
  await assert.rejects(
    readRepositoryEvidence("https://localhost/private", sha, {
      gitFetch: () => assert.fail("SSRF"),
    }),
  );
});

test("lecture GitLab : référence immuable, lecture partielle signalée", async () => {
  let calls = 0;
  const report = await readRepositoryEvidence(
    "https://gitlab.com/groupe/projet",
    sha,
    {
      gitlabToken: "fixture-only",
      gitFetch: async (url, options) => {
        calls++;
        assert.equal(options.headers["PRIVATE-TOKEN"], "fixture-only");
        assert.equal(new URL(url).hostname, "gitlab.com");
        assert.ok(url.includes(sha));
        if (url.includes("/tree?"))
          return Response.json(
            [{ type: "blob", mode: "100644", path: "README.md" }],
            { headers: { "x-next-page": "2" } },
          );
        return new Response(sample[0].content);
      },
    },
  );
  assert.equal(report.partial, true);
  assert.equal(report.milestones[0].observed, true);
  assert.equal(calls, 2);
});

test("bilan persistant, priorité des corrections, publication explicite et conservation sur erreur", async () => {
  const pg = new PGlite();
  const db = {
    query: (...args) => pg.query(...args),
    transaction: (fn) => pg.transaction(fn),
  };
  try {
    await migrate(db);
    const config = {
      password: "long-test-password-2026",
      origin: "http://localhost",
      secure: false,
      gitFetch: fixtureFetch(),
    };
    const app = createApp(db, config);
    const agent = request.agent(app);
    await request(app)
      .post("/api/projects/analyze")
      .set("Origin", config.origin)
      .send({})
      .expect(401);
    await agent
      .post("/api/login")
      .set("Origin", config.origin)
      .send({ password: config.password })
      .expect(200);
    let p = (
      await agent
        .post("/api/projects")
        .set("Origin", config.origin)
        .send({
          student_name: "Démo",
          title: "Calcul de durée",
          repository_url: repository,
        })
        .expect(201)
    ).body;
    const url = `/api/projects/${p.id}`;
    p = (
      await agent
        .post(url + "/analyze")
        .set("Origin", config.origin)
        .send({})
        .expect(200)
    ).body;
    assert.ok(p.milestones.every((m) => m.status === "doing"));
    assert.equal(p.progression.history.length, 1);
    p = (
      await agent
        .put(url + "/milestones/3")
        .set("Origin", config.origin)
        .send({
          status: "done",
          evidence: "PRIVATE_OBSERVATION",
          public_note: "Expliquer le cas vide.",
        })
        .expect(200)
    ).body;
    p = (
      await agent
        .post(url + "/analyze")
        .set("Origin", config.origin)
        .send({})
        .expect(200)
    ).body;
    assert.equal(p.milestones[2].status, "done");
    p = (
      await agent
        .post(url + "/reviews")
        .set("Origin", config.origin)
        .send({
          reviewed_on: "2026-10-27",
          commit_ref: sha,
          achievements: "PUBLIC_ACQUIS",
          next_step: "PUBLIC_NEXT",
          blocker: "PRIVATE_BLOCKER",
          assistance: "PRIVATE_HELP",
        })
        .expect(201)
    ).body;
    assert.equal(publicProgress(p).reviews.length, 0);
    p = (
      await agent
        .put(url + `/reviews/${p.reviews[0].id}/publication`)
        .set("Origin", config.origin)
        .send({ public_visible: true })
        .expect(200)
    ).body;
    p = (
      await agent
        .put(url + "/assessment")
        .set("Origin", config.origin)
        .send({ functionality: 0, comment: "PRIVATE_ASSESSMENT" })
        .expect(200)
    ).body;
    assert.equal(publicProgress(p).assessment, null);
    let exported = JSON.stringify(publicProgress(p));
    for (const secret of [
      "PRIVATE_SOURCE",
      "PRIVATE_OBSERVATION",
      "PRIVATE_BLOCKER",
      "PRIVATE_HELP",
      "PRIVATE_ASSESSMENT",
    ])
      assert.ok(!exported.includes(secret));
    assert.ok(exported.includes("PUBLIC_ACQUIS"));
    assert.ok(exported.includes("Expliquer le cas vide."));
    p = (
      await agent
        .put(url + "/assessment")
        .set("Origin", config.origin)
        .send({
          functionality: 0,
          comment: "Retour public",
          public_visible: true,
        })
        .expect(200)
    ).body;
    assert.equal(publicProgress(p).assessment.scores[0].value, 0);
    config.gitFetch = fixtureFetch({ fail: true });
    p = (
      await agent
        .post(url + "/analyze")
        .set("Origin", config.origin)
        .send({})
        .expect(200)
    ).body;
    assert.equal(p.progression.analysis.sha, sha);
    assert.equal(p.progression.stale, true);
    assert.equal(p.milestones[2].status, "done");
    assert.ok(!JSON.stringify(p.progression).includes("private error"));
    p = (
      await agent
        .put(url + "/milestones/3")
        .set("Origin", config.origin)
        .send({
          status: "done",
          manual_override: false,
          evidence: "PRIVATE_OBSERVATION",
        })
        .expect(200)
    ).body;
    assert.equal(p.milestones[2].status, "doing");
    await migrate(db);
    p = (await agent.get(url).expect(200)).body;
    assert.equal(p.milestones[2].manual_override, false);
    assert.equal(p.milestones[2].status, "doing");
    const publicRows = await exportProgress(db);
    assert.equal(publicRows[0].progression.assessment.scores[0].value, 0);
    config.gitFetch = fixtureFetch();
    await agent
      .post("/api/projects/analyze")
      .set("Origin", config.origin)
      .send({})
      .expect(202);
    for (let i = 0; i < 50; i++) {
      const job = (await agent.get("/api/progression-job").expect(200)).body;
      if (!job.running) {
        assert.equal(job.result.success, 1);
        break;
      }
      if (i === 49) assert.fail("Analyse non terminée");
      await new Promise((resolve) => setTimeout(resolve, 10));
    }
  } finally {
    await pg.close();
  }
});
