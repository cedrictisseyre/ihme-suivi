import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import request from "supertest";
import { PGlite } from "@electric-sql/pglite";
import { migrate } from "../server/db.js";
import { createApp } from "../server/app.js";
import { seed } from "../server/seed.js";
import { date, assessmentInput, projectSignals } from "../server/domain.js";
let pg, db, app, agent;
const origin = "http://localhost:3000";
before(async () => {
  pg = new PGlite();
  db = {
    query: (...a) => pg.query(...a),
    transaction: (fn) => pg.transaction(fn),
  };
  await migrate(db);
  await migrate(db);
  app = createApp(db, {
    password: "test-password-long-enough",
    origin,
    secure: false,
  });
  agent = request.agent(app);
});
after(async () => pg.close());
test("validation des dates, notes et alertes", () => {
  assert.throws(() => date("2026-02-30"));
  assert.throws(() => assessmentInput({ quality: 4 }));
  assert.equal(
    projectSignals({ milestones: [{ status: "done" }] }).progress,
    100,
  );
});
test("parcours protégé : fiche, jalon, revue, évaluation, déconnexion", async () => {
  await request(app).get("/api/projects").expect(401);
  await request(app)
    .post("/api/login")
    .send({ password: "incorrect" })
    .expect(403);
  await request(app)
    .post("/api/login")
    .set("Origin", origin)
    .send({ password: "incorrect" })
    .expect(401);
  const login = await agent
    .post("/api/login")
    .set("Origin", origin)
    .send({ password: "test-password-long-enough" })
    .expect(200);
  assert.match(login.headers["set-cookie"][0], /HttpOnly/);
  assert.match(login.headers["set-cookie"][0], /SameSite=Strict/);
  const p = (
    await agent
      .post("/api/projects")
      .set("Origin", origin)
      .send({ student_name: "Démo", title: "Projet test" })
      .expect(201)
  ).body;
  assert.equal(p.milestones.length, 6);
  await agent
    .put(`/api/projects/${p.id}`)
    .set("Origin", "https://evil.example")
    .send({})
    .expect(403);
  await agent
    .put(`/api/projects/${p.id}/milestones/1`)
    .set("Origin", origin)
    .send({
      status: "blocked",
      evidence: "Relation à clarifier",
      due_date: "2026-11-01",
    })
    .expect(200);
  await agent
    .post(`/api/projects/${p.id}/reviews`)
    .set("Origin", origin)
    .send({
      reviewed_on: "2026-10-26",
      commit_ref: "main",
      achievements: "Acquis",
      next_step: "Tests",
    })
    .expect(400);
  await agent
    .post(`/api/projects/${p.id}/reviews`)
    .set("Origin", origin)
    .send({
      reviewed_on: "2026-10-26",
      commit_ref: "abcdef1",
      achievements: "Acquis",
      blocker: "SQL",
      next_step: "Tests",
    })
    .expect(201);
  const final = (
    await agent
      .put(`/api/projects/${p.id}/assessment`)
      .set("Origin", origin)
      .send({
        functionality: 6,
        design: 4,
        quality: 3,
        progression: 3,
        explanation: 4,
        comment: "Fictif",
      })
      .expect(200)
  ).body;
  assert.equal(final.reviews[0].commit_ref, "abcdef1");
  assert.ok(final.alerts.some((a) => a.kind === "blocked"));
  assert.equal(Number(final.assessment.quality), 3);
  await agent.get("/api/projects/9999").expect(404);
  await agent.get("/api/projects/nope").expect(400);
  await agent.post("/api/logout").set("Origin", origin).send({}).expect(200);
  await agent.get("/api/projects").expect(401);
  // Ancien cookie invalidé côté serveur.
  await request(app)
    .get("/api/projects")
    .set("Cookie", login.headers["set-cookie"][0].split(";")[0])
    .expect(401);
});
test("seed ne modifie jamais une base non vide", async () => {
  await seed(db);
  assert.equal((await db.query("SELECT * FROM projects")).rows.length, 1);
});
test("import de promotion transactionnel et idempotent", async () => {
  const { importRoster } = await import("../server/import-roster.js");
  const rows = [
    {
      student_name: "Étudiant fictif",
      title: "Démo Git",
      repository_url: "https://github.com/demo/fictif",
    },
  ];
  assert.equal((await importRoster(db, rows)).added, 1);
  assert.equal((await importRoster(db, rows)).skipped, 1);
  const count = (await db.query("SELECT count(*) FROM projects")).rows[0].count;
  await assert.rejects(() =>
    importRoster(db, [
      ...rows,
      {
        student_name: "Autre",
        title: "Autre",
        repository_url: "https://evil.example/demo",
      },
    ]),
  );
  assert.equal(
    (await db.query("SELECT count(*) FROM projects")).rows[0].count,
    count,
  );
});
test("synchronisation Git privée : dernier commit persisté dans la promotion", async () => {
  const synced = createApp(db, {
    password: "test-password-long-enough",
    origin,
    secure: false,
    gitFetch: async () => ({
      ok: true,
      json: async () => [
        {
          sha: "a".repeat(40),
          commit: {
            message: "Fonction réelle",
            committer: { date: "2026-10-26T10:00:00Z" },
          },
        },
      ],
    }),
  });
  await request(synced)
    .post("/api/projects/sync")
    .set("Origin", origin)
    .send({})
    .expect(401);
  const teacher = request.agent(synced);
  await teacher
    .post("/api/login")
    .set("Origin", origin)
    .send({ password: "test-password-long-enough" })
    .expect(200);
  const result = (
    await teacher
      .post("/api/projects/sync")
      .set("Origin", origin)
      .send({})
      .expect(200)
  ).body;
  assert.equal(result.success, 1);
  assert.equal(result.failed, 0);
  const projects = (await teacher.get("/api/projects").expect(200)).body;
  assert.equal(
    projects.find((p) => p.repository_url).git.last_sha,
    "a".repeat(40),
  );
});

test("progression combinée : union des validations et indices, priorité enseignante", () => {
  const milestones = [
    { status: "done", manual_override: true, automatic: { observed: true } },
    { status: "doing", manual_override: false, automatic: { observed: true } },
    { status: "todo", manual_override: true, automatic: { observed: true } },
    { status: "blocked", manual_override: true, automatic: { observed: true } },
    { status: "todo", automatic: { observed: false } },
    { status: "todo" },
  ];
  const signals = projectSignals({ milestones });
  assert.equal(signals.progress, 33);
  assert.equal(signals.teacher_progress, 17);
  assert.equal(projectSignals({ milestones: [] }).progress, 0);
  assert.equal(projectSignals({ milestones: [] }).teacher_progress, 0);
});
