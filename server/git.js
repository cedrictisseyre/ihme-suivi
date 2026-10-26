import { InputError } from "./errors.js";
export function repositoryAddress(value) {
  let u;
  try {
    u = new URL(value);
  } catch {
    throw new InputError("Renseigner le dépôt GitHub ou GitLab dans la fiche.");
  }
  if (
    u.protocol !== "https:" ||
    u.port ||
    u.username ||
    u.password ||
    u.search ||
    u.hash ||
    !["github.com", "gitlab.com"].includes(u.hostname)
  )
    throw new InputError(
      "Dépôt : URL HTTPS github.com ou gitlab.com attendue.",
    );
  const parts = u.pathname
    .replace(/\/$/, "")
    .replace(/\.git$/, "")
    .slice(1)
    .split("/");
  if (
    parts.length < 2 ||
    (u.hostname === "github.com" && parts.length !== 2) ||
    parts.some(
      (x) => !x || !/^[A-Za-z0-9_.-]+$/.test(x) || [".", "..", "-"].includes(x),
    )
  )
    throw new InputError("URL du dépôt invalide.");
  return {
    provider: u.hostname === "github.com" ? "github" : "gitlab",
    path: parts.join("/"),
    url: `https://${u.hostname}/${parts.join("/")}`,
  };
}
export async function getActivity(
  value,
  { page = 1, githubToken = "", gitlabToken = "", fetcher = fetch } = {},
) {
  const repo = repositoryAddress(value);
  if (!Number.isInteger(page) || page < 1 || page > 100)
    throw new InputError("Page invalide.");
  const github = repo.provider === "github";
  const url = github
    ? `https://api.github.com/repos/${repo.path}/commits?per_page=20&page=${page}`
    : `https://gitlab.com/api/v4/projects/${encodeURIComponent(repo.path)}/repository/commits?per_page=20&page=${page}`;
  const headers = github
    ? {
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ihme-suivi",
      }
    : {};
  if (github && githubToken) headers.Authorization = `Bearer ${githubToken}`;
  if (!github && gitlabToken) headers["PRIVATE-TOKEN"] = gitlabToken;
  let response;
  try {
    response = await fetcher(url, {
      headers,
      redirect: "error",
      signal: AbortSignal.timeout(8000),
    });
  } catch {
    const e = new Error("Service Git indisponible. Réessayez.");
    e.status = 502;
    throw e;
  }
  if (github && response.status === 409) {
    return {
      repository: repo.url,
      provider: repo.provider,
      page,
      hasNext: false,
      fetchedAt: new Date().toISOString(),
      commits: [],
    };
  }
  if (!response.ok) {
    const e = new Error(
      response.status === 404
        ? "Dépôt introuvable ou privé : vérifier le lien et les droits du jeton serveur."
        : [403, 429].includes(response.status)
          ? "Quota Git atteint ou accès refusé. Réessayez plus tard."
          : response.status === 409
            ? "Dépôt vide : aucun commit disponible."
            : "Lecture du dépôt impossible.",
    );
    e.status = 502;
    throw e;
  }
  const data = await response.json();
  if (!Array.isArray(data)) {
    const e = new Error("Réponse Git inattendue.");
    e.status = 502;
    throw e;
  }
  // Ne transmettre ni email d’auteur, ni jeton, ni réponse brute du fournisseur.
  return {
    repository: repo.url,
    provider: repo.provider,
    page,
    hasNext: data.length === 20,
    fetchedAt: new Date().toISOString(),
    commits: data.map((c) => ({
      sha: github ? c.sha : c.id,
      title: (github ? c.commit.message : c.title).split("\n")[0].slice(0, 300),
      date: github ? c.commit.committer?.date : c.committed_date,
      url: github
        ? `${repo.url}/commit/${c.sha}`
        : `${repo.url}/-/commit/${c.id}`,
    })),
  };
}
