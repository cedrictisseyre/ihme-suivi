import express from "express";
import { syncProjects } from "./sync-git.js";
import { getActivity } from "./git.js";
import helmet from "helmet";
import { rateLimit } from "express-rate-limit";
import { randomBytes, createHash, timingSafeEqual } from "node:crypto";
import path from "node:path";
import {
  projectInput,
  assessmentInput,
  text,
  date,
  MILESTONES,
  CRITERIA,
  projectSignals,
  InputError,
} from "./domain.js";
const hash = (v) => createHash("sha256").update(v).digest("hex");
export function createApp(db, config) {
  if (!config.password || config.password.length < 16)
    throw new Error("ADMIN_PASSWORD : au moins 16 caractères.");
  const app = express();
  app.disable("x-powered-by");
  app.use(
    helmet({ strictTransportSecurity: config.secure ? undefined : false }),
  );
  app.use(express.json({ limit: "32kb" }));
  const cookie = (token) =>
    `ihme_session=${token}; Path=/api; HttpOnly; SameSite=Strict; Max-Age=28800${config.secure ? "; Secure" : ""}`;
  app.get("/api/health", async (req, res) => {
    try {
      await db.query("SELECT 1");
      res.json({ status: "ok", version: config.version || "local" });
    } catch {
      res.status(503).json({ error: "Base indisponible." });
    }
  });
  app.use("/api", (req, res, next) => {
    res.set("Cache-Control", "no-store");
    if (
      ["POST", "PUT", "PATCH"].includes(req.method) &&
      (!req.body || typeof req.body !== "object" || Array.isArray(req.body))
    )
      return res.status(400).json({ error: "Objet JSON attendu." });
    if (
      !["GET", "HEAD", "OPTIONS"].includes(req.method) &&
      req.get("origin") !== config.origin
    )
      return res.status(403).json({ error: "Origine refusée." });
    next();
  });
  app.post(
    "/api/login",
    rateLimit({
      windowMs: 900000,
      limit: 10,
      standardHeaders: "draft-8",
      legacyHeaders: false,
    }),
    async (req, res) => {
      if (
        typeof req.body?.password !== "string" ||
        !timingSafeEqual(
          Buffer.from(hash(req.body.password)),
          Buffer.from(hash(config.password)),
        )
      )
        return res.status(401).json({ error: "Identifiants incorrects." });
      await db.query("DELETE FROM sessions WHERE expires_at < now()");
      const token = randomBytes(32).toString("hex");
      await db.query(
        "INSERT INTO sessions(token_hash,expires_at) VALUES($1,now()+interval '8 hours')",
        [hash(token)],
      );
      res.set("Set-Cookie", cookie(token)).json({ authenticated: true });
    },
  );
  app.use("/api", async (req, res, next) => {
    const token = (req.headers.cookie || "")
      .split(";")
      .map((x) => x.trim())
      .find((x) => x.startsWith("ihme_session="))
      ?.slice(13);
    if (
      !token ||
      !(
        await db.query(
          "SELECT token_hash FROM sessions WHERE token_hash=$1 AND expires_at>now()",
          [hash(token)],
        )
      ).rows.length
    )
      return res.status(401).json({ error: "Connexion enseignant requise." });
    req.token = token;
    next();
  });
  app.get("/api/session", (req, res) => res.json({ authenticated: true }));
  app.post("/api/logout", async (req, res) => {
    await db.query("DELETE FROM sessions WHERE token_hash=$1", [
      hash(req.token),
    ]);
    res.set("Set-Cookie", cookie("") + "; Max-Age=0").json({ ok: true });
  });
  app.get("/api/meta", (req, res) =>
    res.json({ milestones: MILESTONES, criteria: CRITERIA }),
  );
  async function project(id) {
    const p = (await db.query("SELECT * FROM projects WHERE id=$1", [id]))
      .rows[0];
    if (!p) {
      const e = new Error("Projet introuvable.");
      e.status = 404;
      throw e;
    }
    p.milestones = (
      await db.query(
        "SELECT * FROM milestones WHERE project_id=$1 ORDER BY position",
        [id],
      )
    ).rows;
    p.reviews = (
      await db.query(
        "SELECT *, to_char(reviewed_on,'YYYY-MM-DD') AS reviewed_on FROM reviews WHERE project_id=$1 ORDER BY reviews.reviewed_on DESC,id DESC",
        [id],
      )
    ).rows;
    p.git =
      (await db.query("SELECT * FROM git_snapshots WHERE project_id=$1", [id]))
        .rows[0] || null;
    p.assessment =
      (await db.query("SELECT * FROM assessments WHERE project_id=$1", [id]))
        .rows[0] || null;
    p.milestones = p.milestones.map((m) => ({
      ...m,
      due_date: m.due_date
        ? m.due_date instanceof Date
          ? m.due_date.toISOString().slice(0, 10)
          : String(m.due_date).slice(0, 10)
        : null,
    }));
    return { ...p, ...projectSignals(p) };
  }
  app.param("id", (req, res, next, id) => {
    if (!/^[1-9]\d{0,8}$/.test(id))
      return res.status(400).json({ error: "Identifiant invalide." });
    next();
  });
  app.get("/api/projects", async (req, res) => {
    const ids = (
      await db.query("SELECT id FROM projects ORDER BY student_name")
    ).rows;
    res.json(await Promise.all(ids.map((p) => project(p.id))));
  });
  app.post(
    "/api/projects/sync",
    rateLimit({ windowMs: 60000, limit: 1, legacyHeaders: false }),
    async (req, res) => {
      res.json(await syncProjects(db, config));
    },
  );
  app.get(
    "/api/projects/:id/activity",
    rateLimit({ windowMs: 60000, limit: 30, legacyHeaders: false }),
    async (req, res) => {
      const p = await project(req.params.id);
      res.json(
        await getActivity(p.repository_url, {
          page: Number(req.query.page || 1),
          githubToken: config.githubToken,
          gitlabToken: config.gitlabToken,
          fetcher: config.gitFetch,
        }),
      );
    },
  );
  app.get("/api/projects/:id", async (req, res) =>
    res.json(await project(req.params.id)),
  );
  app.post("/api/projects", async (req, res) => {
    const v = projectInput(req.body);
    const id = await db.transaction(async (c) => {
      const p = (
        await c.query(
          "INSERT INTO projects(student_name,title,repository_url,deployed_url,objective) VALUES($1,$2,$3,$4,$5) RETURNING id",
          Object.values(v),
        )
      ).rows[0];
      for (const [i, title] of MILESTONES.entries())
        await c.query(
          "INSERT INTO milestones(project_id,position,title) VALUES($1,$2,$3)",
          [p.id, i + 1, title],
        );
      return p.id;
    });
    res.status(201).json(await project(id));
  });
  app.put("/api/projects/:id", async (req, res) => {
    await project(req.params.id);
    const v = projectInput(req.body);
    await db.query(
      "UPDATE projects SET student_name=$1,title=$2,repository_url=$3,deployed_url=$4,objective=$5,updated_at=now() WHERE id=$6",
      [...Object.values(v), req.params.id],
    );
    res.json(await project(req.params.id));
  });
  app.put("/api/projects/:id/milestones/:position", async (req, res) => {
    await project(req.params.id);
    const v = req.body;
    if (
      !["todo", "doing", "done", "blocked"].includes(v.status) ||
      !/^[1-6]$/.test(req.params.position)
    )
      throw new InputError("Jalon ou statut invalide.");
    await db.query(
      "UPDATE milestones SET status=$1,due_date=$2,evidence=$3,updated_at=now() WHERE project_id=$4 AND position=$5",
      [
        v.status,
        date(v.due_date, false),
        text(v.evidence || "", "Preuve"),
        req.params.id,
        req.params.position,
      ],
    );
    res.json(await project(req.params.id));
  });
  app.post("/api/projects/:id/reviews", async (req, res) => {
    await project(req.params.id);
    const v = req.body;
    const commit = text(v.commit_ref, "Commit", { required: true, max: 40 });
    if (!/^[a-f0-9]{7,40}$/i.test(commit))
      throw new InputError(
        "Commit : SHA Git de 7 à 40 caractères hexadécimaux.",
      );
    await db.query(
      "INSERT INTO reviews(project_id,reviewed_on,commit_ref,achievements,blocker,next_step,assistance) VALUES($1,$2,$3,$4,$5,$6,$7)",
      [
        req.params.id,
        date(v.reviewed_on),
        commit,
        text(v.achievements, "Acquis", { required: true }),
        text(v.blocker || "", "Blocage"),
        text(v.next_step, "Prochaine étape", { required: true }),
        text(v.assistance || "", "Aide"),
      ],
    );
    res.status(201).json(await project(req.params.id));
  });
  app.put("/api/projects/:id/assessment", async (req, res) => {
    await project(req.params.id);
    const v = assessmentInput(req.body);
    const keys = CRITERIA.map((x) => x.key);
    await db.query(
      `INSERT INTO assessments(project_id,${keys.join(",")},comment) VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT(project_id) DO UPDATE SET ${keys.map((k) => `${k}=EXCLUDED.${k}`).join(",")},comment=EXCLUDED.comment,updated_at=now()`,
      [req.params.id, ...keys.map((k) => v[k]), v.comment],
    );
    res.json(await project(req.params.id));
  });
  app.use("/api", (req, res) =>
    res.status(404).json({ error: "Route introuvable." }),
  );
  app.use(express.static(path.resolve("dist")));
  app.get("/{*path}", (req, res) =>
    res.sendFile(path.resolve("dist/index.html")),
  );
  app.use((err, req, res, next) => {
    const status = err.status || 500;
    res.status(status).json({
      error:
        status < 500
          ? err.message
          : "Erreur interne. Réessayez ultérieurement.",
    });
  });
  return app;
}
