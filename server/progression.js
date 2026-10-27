import { automaticEvaluation } from "./automatic-evaluation.js";
import { RUBRIC, ASSESSMENT_GUIDE, RUBRIC_VERSION } from "./rubric.js";
import { repositoryAddress } from "./git.js";

export async function attachProgress(db, project) {
  const report = (
    await db.query(
      "SELECT analysis,error,attempted_at FROM progress_reports WHERE project_id=$1",
      [project.id],
    )
  ).rows[0];
  let analysis = report?.analysis || null;
  let changedRepository = false;
  if (analysis) {
    try {
      changedRepository =
        analysis.repository !== repositoryAddress(project.repository_url).url;
    } catch {
      changedRepository = true;
    }
    if (changedRepository) analysis = null;
  }
  const milestones = project.milestones.map((m) => {
    const automatic =
      analysis?.milestones.find((a) => a.position === m.position) || null;
    return {
      ...m,
      automatic,
      status: m.manual_override ? m.status : automatic?.status || m.status,
    };
  });
  const history = (
    await db.query(
      "SELECT sha,observed,generated_at FROM progress_history WHERE project_id=$1 AND repository=$2 ORDER BY generated_at DESC LIMIT 8",
      [project.id, analysis?.repository || ""],
    )
  ).rows;
  return {
    ...project,
    milestones,
    progression: {
      version: RUBRIC_VERSION,
      analysis,
      evaluation: automaticEvaluation(analysis),
      error: changedRepository
        ? "Dépôt modifié : relancer l’analyse."
        : report?.error || "",
      stale:
        !!analysis &&
        (!!report?.error ||
          (!!project.git?.last_sha &&
            project.git.last_sha !== analysis.sha &&
            Date.parse(project.git.checked_at) >
              Date.parse(analysis.generated_at))),
      history: changedRepository ? [] : history,
      rubric: RUBRIC,
      criteria: ASSESSMENT_GUIDE,
    },
  };
}

// Projection explicite : ne jamais exporter la fiche enseignante brute.
export function publicProgress(project) {
  const progression = project.progression;
  const valid = project.milestones.filter((m) => m.status === "done").length;
  return {
    version: RUBRIC_VERSION,
    generated_at: progression?.analysis?.generated_at || null,
    sha: progression?.analysis?.sha || null,
    stale: !!progression?.stale,
    unavailable: !!progression?.error,
    empty: !!progression?.error?.startsWith("Aucun commit dans ce dépôt"),
    sampled: !!progression?.analysis?.partial,
    evaluation: automaticEvaluation(progression?.analysis),
    validated: valid,
    observed:
      progression?.analysis?.milestones.filter((m) => m.observed).length || 0,
    milestones: RUBRIC.map((rule) => {
      const m = project.milestones.find(
        (item) => item.position === rule.position,
      );
      return {
        ...rule,
        status: m?.status || "todo",
        teacher: !!m?.manual_override,
        public_note: m?.public_note || "",
        automatic: m?.automatic
          ? {
              observed: !!m.automatic.observed,
              summary: m.automatic.summary,
              next: m.automatic.next,
            }
          : null,
      };
    }),
    history: (progression?.history || []).map((h) => ({
      sha: h.sha,
      observed: h.observed,
      generated_at: h.generated_at,
    })),
    reviews: project.reviews
      .filter((r) => r.public_visible)
      .map((r) => ({
        date: String(r.reviewed_on).slice(0, 10),
        achievements: r.achievements,
        next_step: r.next_step,
      })),
    criteria: ASSESSMENT_GUIDE,
    assessment: project.assessment?.public_visible
      ? {
          scores: ASSESSMENT_GUIDE.map((c) => ({
            key: c.key,
            value:
              project.assessment[c.key] == null
                ? null
                : Number(project.assessment[c.key]),
          })),
          comment: project.assessment.comment,
        }
      : null,
  };
}

export async function exportProgress(db) {
  const rows = (await db.query("SELECT id,repository_url FROM projects")).rows;
  const result = [];
  for (const row of rows) {
    const milestones = (
      await db.query(
        "SELECT * FROM milestones WHERE project_id=$1 ORDER BY position",
        [row.id],
      )
    ).rows;
    const reviews = (
      await db.query(
        "SELECT *,to_char(reviewed_on,'YYYY-MM-DD') AS reviewed_on FROM reviews WHERE project_id=$1 ORDER BY reviews.reviewed_on DESC,id DESC",
        [row.id],
      )
    ).rows;
    const assessment = (
      await db.query("SELECT * FROM assessments WHERE project_id=$1", [row.id])
    ).rows[0];
    const git = (
      await db.query(
        "SELECT last_sha,checked_at FROM git_snapshots WHERE project_id=$1",
        [row.id],
      )
    ).rows[0];
    result.push({
      repository_url: row.repository_url,
      progression: publicProgress(
        await attachProgress(db, {
          ...row,
          milestones,
          reviews,
          assessment,
          git,
        }),
      ),
    });
  }
  return result;
}
