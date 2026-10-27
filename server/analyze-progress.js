import { repositoryAddress, getActivity } from "./git.js";
import { RUBRIC, RUBRIC_VERSION } from "./rubric.js";

const groups = [
  {
    position: 1,
    path: /(^|\/)readme\.md$/i,
    content: /[\s\S]{120}/,
    summary: "README descriptif repéré ; vérifier le besoin et le scénario.",
  },
  {
    position: 2,
    path: /\.(sql|[cm]?js|ts)$/i,
    content: /\b(CREATE\s+TABLE|PRIMARY\s+KEY|SELECT|INSERT\s+INTO)\b/i,
    summary:
      "Schéma ou requête SQL repéré ; faire expliquer les données et les clés.",
  },
  {
    position: 3,
    path: /\.[cm]?[jt]sx?$/i,
    content: /\b(for|while)\s*\(|\.(reduce|filter|sort|map)\s*\(|\bif\s*\(/,
    summary:
      "Traitement ou condition repéré ; vérifier son utilité, son résultat et les entrées.",
  },
  {
    position: 4,
    path: /\.[jt]sx?$/i,
    content: /<(form|input|select|button)\b|createElement\s*\(/,
    summary:
      "Élément d’interface repéré ; faire réaliser le scénario principal.",
  },
  {
    position: 5,
    path: /(^|\/)([^/]*(test|spec)[^/]*|readme)\.(md|[cm]?[jt]sx?)$/i,
    content:
      /\b(test|it|assert|expect)\s*[.(]|cas\s+(normal|vide|limite)|résultat\s+attendu/i,
    summary:
      "Essais ou protocole de vérification repérés ; rejouer les cas normal, vide et limite.",
  },
  {
    position: 6,
    path: /(^|\/)(readme\.md|Dockerfile|package\.json)$/i,
    content: /npm\s+(run|ci|install)|docker|https?:\/\//i,
    summary:
      "Instructions ou éléments de livraison repérés ; vérifier le lien et l’explication personnelle.",
  },
];

async function limitedText(response, maximum) {
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximum) throw new Error("Lecture trop volumineuse.");
      chunks.push(Buffer.from(value));
    }
  } finally {
    await reader.cancel();
  }
  return Buffer.concat(chunks).toString("utf8");
}

export function analyzeEvidence(
  files,
  { sha, partial = false, repository = "" },
) {
  return {
    version: RUBRIC_VERSION,
    sha,
    repository,
    generated_at: new Date().toISOString(),
    partial,
    milestones: groups.map((group) => {
      const evidence = files.filter(
        (file) =>
          group.path.test(file.path) && group.content.test(file.content),
      );
      return {
        position: group.position,
        status: evidence.length ? "doing" : "todo",
        observed: evidence.length > 0,
        summary: evidence.length
          ? group.summary
          : "Aucun indice concluant dans les fichiers lus ; à vérifier avec l’enseignant.",
        files: evidence.slice(0, 2).map((file) => file.path),
        next: RUBRIC.find((r) => r.position === group.position).next,
      };
    }),
  };
}

export async function readRepositoryEvidence(repository, sha, config = {}) {
  const repo = repositoryAddress(repository);
  if (!/^[a-f0-9]{40,64}$/i.test(sha)) throw new Error("Commit à actualiser.");
  const github = repo.provider === "github";
  const base = github
    ? `https://api.github.com/repos/${repo.path}`
    : `https://gitlab.com/api/v4/projects/${encodeURIComponent(repo.path)}`;
  const headers = { "User-Agent": "ihme-suivi", Accept: "application/json" };
  if (github && config.githubToken)
    headers.Authorization = `Bearer ${config.githubToken}`;
  if (!github && config.gitlabToken)
    headers["PRIVATE-TOKEN"] = config.gitlabToken;
  const request = async (suffix, maximum) => {
    const response = await (config.gitFetch || fetch)(base + suffix, {
      headers,
      redirect: "error",
      signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) throw new Error("Lecture du dépôt indisponible.");
    return { response, text: await limitedText(response, maximum) };
  };
  const tree = await request(
    github
      ? `/git/trees/${sha}?recursive=1`
      : `/repository/tree?ref=${sha}&recursive=true&per_page=100&page=1`,
    2_000_000,
  );
  const listing = JSON.parse(tree.text);
  const entries = github ? listing.tree : listing;
  if (!Array.isArray(entries)) throw new Error("Arborescence indisponible.");
  const partialTree = github
    ? !!listing.truncated
    : !!tree.response.headers.get("x-next-page") || entries.length === 100;
  const safe = entries.filter(
    (entry) =>
      entry.type === "blob" &&
      ["100644", "100755"].includes(entry.mode) &&
      typeof entry.path === "string" &&
      entry.path.length <= 200 &&
      !/[\r\n\x00]/.test(entry.path) &&
      !/(^|\/)(node_modules|vendor|dist|build|\.git)(\/|$)/.test(entry.path) &&
      !/(^|\/)\./.test(entry.path) &&
      (!github || entry.size <= 50_000),
  );
  const selected = [
    ...new Set(
      groups.flatMap((group) =>
        safe
          .filter((entry) => group.path.test(entry.path))
          .sort((a, b) => {
            const rank = (entry) =>
              group.position === 2
                ? /\.sql$/i.test(entry.path)
                  ? 0
                  : /schema|migrat|database|\bdb\b/i.test(entry.path)
                    ? 1
                    : 2
                : group.position === 3
                  ? /calcul|algorithm|util|domain|service|server|controller/i.test(
                      entry.path,
                    )
                    ? 0
                    : 1
                  : entry.path.split("/").length;
            return rank(a) - rank(b) || a.path.localeCompare(b.path);
          })
          .slice(0, 2),
      ),
    ),
  ];
  const files = [];
  let skipped = false;
  for (const entry of selected) {
    // URL reconstruite depuis une identité validée : jamais l’URL d’un objet distant.
    if (github && !/^[a-f0-9]{40,64}$/i.test(entry.sha)) {
      skipped = true;
      continue;
    }
    const result = await request(
      github
        ? `/git/blobs/${entry.sha}`
        : `/repository/files/${encodeURIComponent(entry.path)}/raw?ref=${sha}`,
      100_000,
    );
    const data = github ? JSON.parse(result.text) : null;
    if (
      github &&
      (data.encoding !== "base64" || typeof data.content !== "string")
    )
      throw new Error("Contenu indisponible.");
    const content = github
      ? Buffer.from(data.content, "base64").toString("utf8")
      : result.text;
    if (Buffer.byteLength(content) > 50_000) {
      skipped = true;
      continue;
    }
    files.push({ path: entry.path, content });
  }
  return analyzeEvidence(files, {
    sha,
    repository: repo.url,
    partial: partialTree || skipped || safe.length > selected.length,
  });
}

const active = new Set();
export async function analyzeProject(db, project, config = {}) {
  if (active.has(project.id)) return { skipped: true };
  active.add(project.id);
  try {
    const activity = await getActivity(project.repository_url, {
      perPage: 1,
      githubToken: config.githubToken,
      gitlabToken: config.gitlabToken,
      fetcher: config.gitFetch,
    });
    const sha = activity.commits[0]?.sha;
    if (!sha) throw new Error("Dépôt sans commit.");
    const previous = (
      await db.query(
        "SELECT analysis,error FROM progress_reports WHERE project_id=$1",
        [project.id],
      )
    ).rows[0];
    if (
      previous?.analysis?.sha === sha &&
      previous.analysis.repository ===
        repositoryAddress(project.repository_url).url &&
      previous.analysis.version === RUBRIC_VERSION &&
      !previous.error &&
      !config.force
    )
      return { skipped: true };
    const analysis = await readRepositoryEvidence(
      project.repository_url,
      sha,
      config,
    );
    await db.query(
      "INSERT INTO progress_reports(project_id,analysis) VALUES($1,$2) ON CONFLICT(project_id) DO UPDATE SET analysis=EXCLUDED.analysis,error='',attempted_at=now()",
      [project.id, JSON.stringify(analysis)],
    );
    await db.query(
      "INSERT INTO progress_history(project_id,sha,version,observed,repository) VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING",
      [
        project.id,
        sha,
        RUBRIC_VERSION,
        analysis.milestones.filter((m) => m.observed).length,
        analysis.repository,
      ],
    );
    return { success: true };
  } catch {
    // Aucun message du fournisseur, contenu ou secret n’est persisté ni publié.
    await db.query(
      "INSERT INTO progress_reports(project_id,error) VALUES($1,$2) ON CONFLICT(project_id) DO UPDATE SET error=EXCLUDED.error,attempted_at=now()",
      [
        project.id,
        "Analyse indisponible : vérifier le dépôt, ses droits ou le quota. Le dernier bilan réussi est conservé.",
      ],
    );
    return { failed: true };
  } finally {
    active.delete(project.id);
  }
}

export async function analyzePromotion(db, config = {}) {
  const rows = (
    await db.query(
      "SELECT id,repository_url FROM projects WHERE repository_url<>'' ORDER BY id",
    )
  ).rows;
  const result = { success: 0, failed: 0, skipped: 0 };
  for (let i = 0; i < rows.length; i += 2) {
    const outcomes = await Promise.all(
      rows.slice(i, i + 2).map((p) => analyzeProject(db, p, config)),
    );
    for (const outcome of outcomes)
      for (const key of Object.keys(result)) if (outcome[key]) result[key]++;
  }
  return result;
}
