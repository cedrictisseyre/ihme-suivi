import { analyzePromotion } from "./analyze-progress.js";
import { getCommitSummary } from "./git.js";
import { createDatabase } from "./db.js";

export async function syncProjects(db, config = {}) {
  const projects = (
    await db.query(
      "SELECT id,repository_url FROM projects WHERE repository_url<>'' ORDER BY id",
    )
  ).rows;
  let success = 0,
    failed = 0;
  for (let i = 0; i < projects.length; i += 3)
    await Promise.all(
      projects.slice(i, i + 3).map(async (p) => {
        try {
          const { last, activity } = await getCommitSummary(p.repository_url, {
            githubToken: config.githubToken,
            gitlabToken: config.gitlabToken,
            fetcher: config.gitFetch,
          });
          await db.query(
            "INSERT INTO git_snapshots(project_id,last_sha,last_title,last_committed_at,daily_activity) VALUES($1,$2,$3,$4,$5) ON CONFLICT(project_id) DO UPDATE SET last_sha=EXCLUDED.last_sha,last_title=EXCLUDED.last_title,last_committed_at=EXCLUDED.last_committed_at,daily_activity=EXCLUDED.daily_activity,checked_at=now(),error=''",
            [
              p.id,
              last?.sha || null,
              last?.title || null,
              last?.date || null,
              JSON.stringify(activity),
            ],
          );
          success++;
        } catch (e) {
          await db.query(
            "INSERT INTO git_snapshots(project_id,error) VALUES($1,$2) ON CONFLICT(project_id) DO UPDATE SET error=EXCLUDED.error,checked_at=now()",
            [
              p.id,
              e.status && e.status <= 502
                ? e.message
                : "Lecture Git impossible : vérifier le lien, les droits ou le quota.",
            ],
          );
          failed++;
        }
      }),
    );
  return { success, failed };
}
if (process.argv[1]?.endsWith("/sync-git.js")) {
  const db = createDatabase(process.env.DATABASE_URL);
  try {
    console.log(
      JSON.stringify(
        await syncProjects(db, {
          githubToken: process.env.GITHUB_TOKEN,
          gitlabToken: process.env.GITLAB_TOKEN,
        }),
      ),
    );
    console.log(
      JSON.stringify({
        progression: await analyzePromotion(db, {
          useSnapshots: true,
          githubToken: process.env.GITHUB_TOKEN,
          gitlabToken: process.env.GITLAB_TOKEN,
        }),
      }),
    );
  } finally {
    await db.close();
  }
}
