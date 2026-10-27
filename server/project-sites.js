import { readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";

const repositoryKey = (value = "") =>
  value
    .trim()
    .replace(/\/+$/, "")
    .replace(/\.git$/i, "")
    .toLowerCase();

export async function projectSite(project, config) {
  let assignments;
  try {
    assignments = JSON.parse(
      await readFile(
        config.galleryProjectsPath || "/run/ihme-gallery/projects.json",
        "utf8",
      ),
    );
  } catch {
    return null;
  }
  if (!Array.isArray(assignments) || !project.repository_url) return null;
  const assignment = assignments.find(
    (row) =>
      repositoryKey(row.repository) === repositoryKey(project.repository_url),
  );
  // Les numéros viennent du provisionnement, jamais de l’ordre des fiches SQL.
  if (!assignment || !/^p(?:0[1-9]|1[0-9]|20)$/.test(assignment.id))
    return null;
  let url = project.deployed_url || "";
  if (config.studentOrigin && /^[a-z0-9][a-z0-9-]*$/.test(assignment.slug)) {
    url = new URL(`/${assignment.slug}/`, config.studentOrigin).href;
  }
  let thumbnail = null;
  try {
    const files = await readdir(
      config.previewsPath || "/run/ihme-gallery/public/previews",
    );
    const candidates = files.filter((name) =>
      new RegExp(`^${assignment.id}-[a-f0-9]{64}\\.jpg$`).test(name),
    );
    const dated = await Promise.all(
      candidates.map(async (name) => ({
        name,
        modified: (
          await stat(
            path.join(
              config.previewsPath || "/run/ihme-gallery/public/previews",
              name,
            ),
          )
        ).mtimeMs,
      })),
    );
    dated.sort((a, b) => b.modified - a.modified);
    if (dated.length) thumbnail = `/api/project-previews/${dated[0].name}`;
  } catch {
    // La fiche reste disponible avant la première capture ou en développement local.
  }
  return {
    id: assignment.id,
    label: `P${Number(assignment.id.slice(1))}`,
    url,
    thumbnail,
    progress_url: config.studentOrigin
      ? new URL(`/progression/${assignment.id}/`, config.studentOrigin).href
      : null,
  };
}
