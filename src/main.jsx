import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import CommitChart from "./CommitChart.jsx";
async function api(url, method = "GET", body) {
  const r = await fetch("/api" + url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json();
  if (!r.ok) {
    const e = new Error(data.error);
    e.status = r.status;
    throw e;
  }
  return data;
}
const labels = {
  todo: "À faire",
  doing: "En cours",
  done: "Validé",
  blocked: "Bloqué",
};
function Field({
  label,
  name,
  value,
  onChange,
  type = "text",
  required = false,
  maxLength = 3000,
  ...props
}) {
  return (
    <label>
      {label}
      {type === "textarea" ? (
        <textarea
          name={name}
          value={value ?? ""}
          onChange={onChange}
          required={required}
          maxLength={maxLength}
          {...props}
        />
      ) : (
        <input
          name={name}
          type={type}
          value={value ?? ""}
          onChange={onChange}
          required={required}
          maxLength={maxLength}
          {...props}
        />
      )}
    </label>
  );
}
function App() {
  const [auth, setAuth] = useState(false),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [projects, setProjects] = useState([]),
    [selected, setSelected] = useState(null),
    [query, setQuery] = useState(""),
    [filter, setFilter] = useState("all"),
    [meta, setMeta] = useState({ criteria: [] }),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  async function run(fn) {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(e.message);
      if (e.status === 401) {
        setAuth(false);
        setProjects([]);
        setSelected(null);
      }
    } finally {
      setBusy(false);
    }
  }
  async function load() {
    const [p, m] = await Promise.all([api("/projects"), api("/meta")]);
    setProjects(p);
    setMeta(m);
  }
  useEffect(() => {
    api("/session")
      .then(async () => {
        setAuth(true);
        await load();
      })
      .catch((e) => {
        if (e.status !== 401) setError(e.message);
      })
      .finally(() => setLoading(false));
  }, []);
  async function save(url, method, v) {
    const p = await api(url, method, v);
    setProjects((ps) =>
      ps.some((x) => x.id === p.id)
        ? ps.map((x) => (x.id === p.id ? p : x))
        : [...ps, p],
    );
    setSelected(p);
    setNotice("Enregistrement effectué.");
  }
  const current = projects.find((p) => p.id === selected?.id);
  return (
    <>
      <header>
        <a href="#" onClick={() => setSelected(null)} className="brand">
          <span className="mark">i.</span> IHME{" "}
          <small>Atelier de projets</small>
        </a>
        {auth && (
          <button
            className="ghost"
            onClick={() =>
              run(async () => {
                await api("/logout", "POST", {});
                setAuth(false);
                setProjects([]);
                setSelected(null);
              })
            }
          >
            Se déconnecter
          </button>
        )}
      </header>
      <main>
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {notice && (
          <div className="notice" role="status">
            {notice}
          </div>
        )}
        {loading ? (
          <p>Chargement…</p>
        ) : !auth ? (
          <section className="login">
            <p className="eyebrow">ESPACE ENSEIGNANT</p>
            <h1>
              Chaque projet,
              <br />
              une progression.
            </h1>
            <p>
              Les jalons, les échanges et les prochaines étapes de votre
              promotion, réunis dans un carnet de suivi.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const password = new FormData(e.currentTarget).get("password");
                run(async () => {
                  await api("/login", "POST", { password });
                  setAuth(true);
                  await load();
                });
              }}
            >
              <label>
                Mot de passe enseignant
                <input
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                />
              </label>
              <button disabled={busy}>Ouvrir le carnet →</button>
            </form>
            <small>Accès réservé à l’enseignant.</small>
          </section>
        ) : current ? (
          <Detail
            key={current.id}
            p={current}
            meta={meta}
            busy={busy}
            back={() => setSelected(null)}
            save={(url, method, v) => run(() => save(url, method, v))}
          />
        ) : selected === "new" ? (
          <>
            <button className="ghost" onClick={() => setSelected(null)}>
              ← Promotion
            </button>
            <h1>Une nouvelle fiche</h1>
            <ProjectForm
              busy={busy}
              onSave={(v) => run(() => save("/projects", "POST", v))}
            />
          </>
        ) : (
          <>
            <div className="titlebar">
              <div>
                <p className="eyebrow">REACT · EXPRESS · POSTGRESQL</p>
                <h1>La promotion</h1>
                <p>Accompagner les projets, rendre les progrès visibles.</p>
              </div>
              <div className="actions">
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    run(async () => {
                      const r = await api("/projects/sync", "POST", {});
                      await load();
                      setNotice(
                        `${r.success} dépôts lus, ${r.failed} lectures à vérifier.`,
                      );
                    })
                  }
                >
                  {busy ? "Lecture en cours…" : "Actualiser les dépôts Git"}
                </button>
                <button onClick={() => setSelected("new")}>
                  + Ajouter une fiche
                </button>
              </div>
            </div>
            <div className="stats">
              <article>
                <strong>{projects.length}</strong>projets suivis
              </article>
              <article>
                <strong>
                  {
                    projects.filter((p) =>
                      p.alerts.some((a) =>
                        ["blocked", "blocker"].includes(a.kind),
                      ),
                    ).length
                  }
                </strong>
                projets avec blocage
              </article>
              <article>
                <strong>
                  {projects.length
                    ? Math.round(
                        projects.reduce((n, p) => n + p.progress, 0) /
                          projects.length,
                      )
                    : 0}
                  %
                </strong>
                jalons validés en moyenne
              </article>
            </div>
            <div className="toolbar">
              <input
                aria-label="Rechercher dans la promotion"
                placeholder="Rechercher un étudiant, un projet…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <select
                aria-label="Filtrer les projets"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="all">Tous les projets</option>
                <option value="alerts">Avec une alerte</option>
                <option value="blocked">Avec un blocage</option>
              </select>
            </div>
            <div className="cards">
              {projects
                .filter(
                  (p) =>
                    (p.student_name + " " + p.title)
                      .toLowerCase()
                      .includes(query.toLowerCase()) &&
                    (filter === "all" ||
                      (filter === "alerts" && p.alerts.length) ||
                      (filter === "blocked" &&
                        p.alerts.some((a) =>
                          ["blocked", "blocker"].includes(a.kind),
                        ))),
                )
                .map((p) => (
                  <button
                    className="card"
                    key={p.id}
                    onClick={() => setSelected(p)}
                  >
                    <span className="eyebrow">{p.student_name}</span>
                    <h2>{p.title}</h2>
                    {p.objective && (
                      <p className="card-objective">{p.objective}</p>
                    )}
                    <div className="git-summary">
                      {p.git ? (
                        <>
                          <p>
                            {p.git.error ||
                              (p.git.last_sha
                                ? `Dernier commit : ${p.git.last_sha.slice(0, 7)} · ${new Date(p.git.last_committed_at).toLocaleDateString("fr-FR")}`
                                : "Dépôt sans commit")}
                          </p>
                          {!p.git.error && <p>{p.git.last_title}</p>}
                          <small>
                            Vérifié le{" "}
                            {new Date(p.git.checked_at).toLocaleString("fr-FR")}
                          </small>
                        </>
                      ) : (
                        <p>Activité Git à actualiser</p>
                      )}
                    </div>
                    <CommitChart
                      activity={p.git?.daily_activity}
                      stale={!!p.git?.error}
                    />
                    <div className="progress">
                      <span style={{ width: p.progress + "%" }} />
                    </div>
                    <div className="between">
                      <span>{p.progress}% des jalons validés</span>
                      <b>Ouvrir ↗</b>
                    </div>
                    <div className="tags">
                      {p.alerts.map((a) => (
                        <span key={a.kind}>{a.label}</span>
                      ))}
                    </div>
                  </button>
                ))}
            </div>
            {!projects.length && (
              <p>Aucune fiche. Ajoutez votre premier projet.</p>
            )}
          </>
        )}
      </main>
      <footer>IHME · Carnet pédagogique · Suivi de promotion</footer>
    </>
  );
}
function ProjectForm({ p = {}, onSave, busy }) {
  const [v, setV] = useState({
    student_name: p.student_name || "",
    title: p.title || "",
    repository_url: p.repository_url || "",
    deployed_url: p.deployed_url || "",
    objective: p.objective || "",
  });
  return (
    <form
      className="panel formgrid"
      onSubmit={(e) => {
        e.preventDefault();
        onSave(v);
      }}
    >
      {[
        ["student_name", "Identifiant étudiant", 120],
        ["title", "Titre du projet", 180],
        ["repository_url", "Dépôt GitHub ou GitLab", 1000],
        ["deployed_url", "Application déployée", 1000],
        ["objective", "Objectif", 3000],
      ].map(([key, label, max]) => (
        <Field
          key={key}
          name={key}
          label={label}
          maxLength={max}
          type={
            key === "objective"
              ? "textarea"
              : key.endsWith("url")
                ? "url"
                : "text"
          }
          required={["student_name", "title"].includes(key)}
          value={v[key]}
          onChange={(e) => setV({ ...v, [key]: e.target.value })}
        />
      ))}
      <button disabled={busy}>Enregistrer la fiche</button>
    </form>
  );
}
function Detail({ p, meta, busy, back, save }) {
  const [tab, setTab] = useState("activity");
  const [chosen, setChosen] = useState("");
  return (
    <>
      <button className="ghost" onClick={back}>
        ← Toute la promotion
      </button>
      <p className="eyebrow">{p.student_name}</p>
      <h1>{p.title}</h1>
      <p>{p.objective}</p>
      <div className="links">
        {p.repository_url && (
          <a href={p.repository_url} target="_blank" rel="noreferrer">
            Dépôt source ↗
          </a>
        )}
        {p.deployed_url && (
          <a href={p.deployed_url} target="_blank" rel="noreferrer">
            Application ↗
          </a>
        )}
      </div>
      <div className="tabs" role="tablist" aria-label="Contenu de la fiche">
        {[
          ["activity", "Activité Git"],
          ["milestones", "Jalons"],
          ["reviews", "Journal des revues"],
          ["assessment", "Évaluation facultative"],
          ["project", "Fiche projet"],
        ].map(([k, t]) => (
          <button
            role="tab"
            aria-selected={tab === k}
            key={k}
            onClick={() => setTab(k)}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "activity" && (
        <GitActivity
          p={p}
          choose={(sha) => {
            setChosen(sha);
            setTab("reviews");
          }}
        />
      )}
      {tab === "project" && (
        <ProjectForm
          p={p}
          busy={busy}
          onSave={(v) => save(`/projects/${p.id}`, "PUT", v)}
        />
      )}
      {tab === "milestones" && (
        <div className="milestones">
          {p.milestones.map((m) => (
            <Milestone
              key={m.id}
              m={m}
              busy={busy}
              onSave={(v) =>
                save(`/projects/${p.id}/milestones/${m.position}`, "PUT", v)
              }
            />
          ))}
        </div>
      )}
      {tab === "reviews" && (
        <div className="reviewgrid">
          <ReviewForm
            initialCommit={chosen}
            busy={busy}
            onSave={(v) => save(`/projects/${p.id}/reviews`, "POST", v)}
          />
          <div>
            <h2>Historique des échanges</h2>
            {p.reviews.length === 0 && <p>La première revue reste à écrire.</p>}
            {p.reviews.map((r) => (
              <article className="panel review" key={r.id}>
                <p className="eyebrow">
                  {r.reviewed_on} · Commit <code>{r.commit_ref}</code>
                </p>
                {[
                  ["Acquis", r.achievements],
                  ["Blocage", r.blocker],
                  ["Prochaine étape", r.next_step],
                  ["Accompagnement", r.assistance],
                ].map(
                  ([k, v]) =>
                    v && (
                      <div key={k}>
                        <h3>{k}</h3>
                        <p>{v}</p>
                      </div>
                    ),
                )}
              </article>
            ))}
          </div>
        </div>
      )}
      {tab === "assessment" && (
        <Assessment
          key={JSON.stringify(p.assessment)}
          a={p.assessment || {}}
          criteria={meta.criteria}
          busy={busy}
          onSave={(v) => save(`/projects/${p.id}/assessment`, "PUT", v)}
        />
      )}
    </>
  );
}
function Milestone({ m, onSave, busy }) {
  const [v, setV] = useState(m);
  useEffect(() => setV(m), [m]);
  return (
    <form
      className="panel milestone"
      onSubmit={(e) => {
        e.preventDefault();
        onSave(v);
      }}
    >
      <span className="number">0{m.position}</span>
      <h2>{m.title}</h2>
      <label>
        Statut
        <select
          value={v.status}
          onChange={(e) => setV({ ...v, status: e.target.value })}
        >
          {Object.entries(labels).map(([k, t]) => (
            <option key={k} value={k}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <Field
        label="Échéance"
        type="date"
        value={v.due_date}
        onChange={(e) => setV({ ...v, due_date: e.target.value })}
      />
      <Field
        label="Preuve / observation"
        type="textarea"
        value={v.evidence}
        onChange={(e) => setV({ ...v, evidence: e.target.value })}
      />
      <button disabled={busy} className="secondary">
        Enregistrer
      </button>
    </form>
  );
}
function ReviewForm({ onSave, busy, initialCommit }) {
  const blank = () => ({
    reviewed_on: new Date().toISOString().slice(0, 10),
    commit_ref: initialCommit || "",
    achievements: "",
    blocker: "",
    next_step: "",
    assistance: "",
  });
  const [v, setV] = useState(blank);
  return (
    <form
      className="panel"
      onSubmit={(e) => {
        e.preventDefault();
        onSave(v);
      }}
    >
      <h2>Consigner une revue</h2>
      {[
        ["reviewed_on", "Date de la revue", "date", true],
        ["commit_ref", "Commit examiné (SHA Git)", "text", true],
        ["achievements", "Acquis / éléments examinés", "textarea", true],
        ["blocker", "Blocage actuel", "textarea", false],
        ["next_step", "Prochaine étape concrète", "textarea", true],
        ["assistance", "Aide apportée", "textarea", false],
      ].map(([k, t, type, required]) => (
        <Field
          key={k}
          label={t}
          type={type}
          value={v[k]}
          required={required}
          maxLength={k === "commit_ref" ? 40 : 3000}
          pattern={k === "commit_ref" ? "[a-fA-F0-9]{7,40}" : undefined}
          onChange={(e) => setV({ ...v, [k]: e.target.value })}
        />
      ))}
      <button disabled={busy}>Ajouter au journal</button>
      <p className="muted">
        Les revues sont conservées pour retracer la progression. Une nouvelle
        revue actualise le blocage signalé.
      </p>
    </form>
  );
}
function GitActivity({ p, choose }) {
  const [data, setData] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function load(page = 1) {
    setBusy(true);
    setError("");
    try {
      setData(await api(`/projects/${p.id}/activity?page=${page}`));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <div className="titlebar">
        <div>
          <h2>Le travail dans le dépôt</h2>
          <p>
            Commits réels de la branche par défaut. Choisissez la version à
            examiner en revue.
          </p>
        </div>
        <button disabled={busy || !p.repository_url} onClick={() => load()}>
          Lire le dépôt Git
        </button>
      </div>
      {!p.repository_url && (
        <p>Renseignez le dépôt de l’étudiant dans l’onglet « Fiche projet ».</p>
      )}
      {busy && <p role="status">Lecture du dépôt…</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {data && (
        <>
          <p className="muted">
            Lecture du {new Date(data.fetchedAt).toLocaleString("fr-FR")} · page{" "}
            {data.page}. Cette activité ne constitue pas une évaluation.
          </p>
          {data.commits.length === 0 && <p>Aucun commit sur cette page.</p>}
          {data.commits.map((c) => (
            <article className="panel commit" key={c.sha}>
              <div>
                <a href={c.url} target="_blank" rel="noreferrer">
                  <code>{c.sha.slice(0, 10)}</code> · {c.title} ↗
                </a>
                <p>{new Date(c.date).toLocaleString("fr-FR")}</p>
              </div>
              <button className="secondary" onClick={() => choose(c.sha)}>
                Examiner en revue
              </button>
            </article>
          ))}
          <div className="toolbar">
            <button
              disabled={busy || data.page === 1}
              onClick={() => load(data.page - 1)}
            >
              ← Précédents
            </button>
            <button
              disabled={busy || !data.hasNext}
              onClick={() => load(data.page + 1)}
            >
              Suivants →
            </button>
          </div>
        </>
      )}
    </section>
  );
}
function Assessment({ a, criteria, onSave, busy }) {
  const [v, setV] = useState(a);
  const complete = criteria.every(
    (c) => v[c.key] !== "" && v[c.key] !== undefined && v[c.key] !== null,
  );
  return (
    <form
      className="panel assessment"
      onSubmit={(e) => {
        e.preventDefault();
        onSave(v);
      }}
    >
      <p className="eyebrow">GRILLE FACULTATIVE</p>
      <h2>Évaluer la progression</h2>
      <p>
        Les critères peuvent rester vides. Le total est affiché une fois la
        grille complète.
      </p>
      {criteria.map((c) => (
        <Field
          key={c.key}
          label={`${c.title} / ${c.max}`}
          type="number"
          min="0"
          max={c.max}
          step="0.5"
          value={v[c.key]}
          onChange={(e) =>
            setV({
              ...v,
              [c.key]: e.target.value === "" ? null : Number(e.target.value),
            })
          }
        />
      ))}
      <Field
        label="Appréciation pédagogique"
        type="textarea"
        value={v.comment}
        onChange={(e) => setV({ ...v, comment: e.target.value })}
      />
      <p className="total">
        {complete
          ? criteria.reduce((n, c) => n + Number(v[c.key]), 0) + " / 20"
          : "Grille incomplète"}
      </p>
      <button disabled={busy}>Enregistrer l’évaluation</button>
    </form>
  );
}
createRoot(document.getElementById("root")).render(<App />);
