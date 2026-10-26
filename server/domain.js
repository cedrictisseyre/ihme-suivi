import { repositoryAddress } from "./git.js";
export const MILESTONES = [
  "Cadrage du besoin",
  "Modèle de données",
  "API et règles métier",
  "Interface React",
  "Intégration et tests",
  "Déploiement et documentation",
];
export const CRITERIA = [
  { key: "functionality", title: "Fonctionnement", max: 6 },
  { key: "design", title: "Conception", max: 4 },
  { key: "quality", title: "Qualité du code", max: 3 },
  { key: "progression", title: "Progression", max: 3 },
  { key: "explanation", title: "Compréhension et explication", max: 4 },
];
import { InputError } from "./errors.js";
export { InputError } from "./errors.js";
export function text(value, label, { required = false, max = 3000 } = {}) {
  if (typeof value !== "string")
    throw new InputError(`${label} : texte attendu.`);
  const v = value.trim();
  if ((required && !v) || v.length > max)
    throw new InputError(
      `${label} : ${required ? "champ obligatoire, " : ""}${max} caractères maximum.`,
    );
  return v;
}
export function webUrl(value, repository = false) {
  const v = text(value, "Lien", { max: 1000 });
  if (!v) return "";
  let u;
  try {
    u = new URL(v);
  } catch {
    throw new InputError("Adresse web invalide.");
  }
  if (!["https:", "http:"].includes(u.protocol) || u.username || u.password)
    throw new InputError("Utiliser une URL HTTP(S) sans identifiant.");
  if (repository && !["github.com", "gitlab.com"].includes(u.hostname))
    throw new InputError(
      "Le dépôt doit être hébergé sur github.com ou gitlab.com.",
    );
  if (repository) return repositoryAddress(v).url;
  return u.href;
}
export function date(value, required = true) {
  if (!value && !required) return null;
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
    throw new InputError("Date attendue au format AAAA-MM-JJ.");
  const d = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== value)
    throw new InputError("Date invalide.");
  return value;
}
export function projectInput(v) {
  return {
    student_name: text(v.student_name, "Étudiant", {
      required: true,
      max: 120,
    }),
    title: text(v.title, "Projet", { required: true, max: 180 }),
    repository_url: webUrl(v.repository_url || "", true),
    deployed_url: webUrl(v.deployed_url || ""),
    objective: text(v.objective || "", "Objectif"),
  };
}
export function assessmentInput(v) {
  const out = { comment: text(v.comment || "", "Appréciation") };
  for (const { key, max } of CRITERIA) {
    const n = v[key];
    if (n === null || n === "" || n === undefined) {
      out[key] = null;
      continue;
    }
    if (typeof n !== "number" || !Number.isFinite(n) || n < 0 || n > max)
      throw new InputError(`Note ${key} : valeur entre 0 et ${max}.`);
    out[key] = n;
  }
  return out;
}
export function projectSignals(
  project,
  today = new Date().toISOString().slice(0, 10),
) {
  const alerts = [];
  const m = project.milestones || [];
  if (m.some((x) => x.status === "blocked"))
    alerts.push({ kind: "blocked", label: "Jalon bloqué" });
  if (
    m.some(
      (x) =>
        x.due_date &&
        String(x.due_date).slice(0, 10) < today &&
        x.status !== "done",
    )
  )
    alerts.push({ kind: "late", label: "Échéance dépassée" });
  const last = project.reviews?.[0];
  if (last?.blocker)
    alerts.push({
      kind: "blocker",
      label: "Blocage signalé à la dernière revue",
    });
  if (!last)
    alerts.push({ kind: "review", label: "Première revue à planifier" });
  else if (
    Math.floor(
      (Date.parse(today) - Date.parse(String(last.reviewed_on).slice(0, 10))) /
        86400000,
    ) > 14
  )
    alerts.push({ kind: "stale", label: "Revue datant de plus de 14 jours" });
  if (!project.repository_url)
    alerts.push({ kind: "repo", label: "Dépôt à renseigner" });
  if (
    m.some((x) => x.position === 6 && x.status === "done") &&
    !project.deployed_url
  )
    alerts.push({
      kind: "deployment",
      label: "URL de déploiement à renseigner",
    });
  return {
    progress: m.length
      ? Math.round(
          (100 * m.filter((x) => x.status === "done").length) / m.length,
        )
      : 0,
    alerts,
  };
}
