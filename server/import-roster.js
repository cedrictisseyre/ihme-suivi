// Entrée JSON sur stdin : aucun fichier étudiant n'est nécessaire dans le dépôt.
import { createDatabase } from "./db.js";
import { projectInput, MILESTONES } from "./domain.js";
export async function importRoster(db, rows) {
  if (!Array.isArray(rows) || rows.length > 500)
    throw new Error("Liste JSON attendue, 500 fiches maximum.");
  const values = rows.map(projectInput);
  if (values.some((v) => !v.repository_url))
    throw new Error("Chaque fiche importée doit avoir un dépôt.");
  if (
    new Set(values.map((v) => v.repository_url.toLowerCase())).size !==
    values.length
  )
    throw new Error("Dépôt dupliqué dans la liste.");
  return db.transaction(async (c) => {
    await c.query("SELECT pg_advisory_xact_lock(7261041)");
    let added = 0,
      skipped = 0;
    for (const v of values) {
      if (
        (
          await c.query(
            "SELECT id FROM projects WHERE lower(repository_url)=lower($1)",
            [v.repository_url],
          )
        ).rows.length
      ) {
        skipped++;
        continue;
      }
      const { id } = (
        await c.query(
          "INSERT INTO projects(student_name,title,repository_url,deployed_url,objective) VALUES($1,$2,$3,$4,$5) RETURNING id",
          Object.values(v),
        )
      ).rows[0];
      for (const [i, title] of MILESTONES.entries())
        await c.query(
          "INSERT INTO milestones(project_id,position,title) VALUES($1,$2,$3)",
          [id, i + 1, title],
        );
      added++;
    }
    return { added, skipped };
  });
}
if (process.argv[1]?.endsWith("/import-roster.js")) {
  const db = createDatabase(process.env.DATABASE_URL);
  try {
    let input = "";
    for await (const chunk of process.stdin) {
      input += chunk;
      if (input.length > 2_000_000) throw new Error("Entrée trop volumineuse.");
    }
    const result = await importRoster(db, JSON.parse(input));
    console.log(
      `${result.added} fiches importées, ${result.skipped} dépôts déjà présents.`,
    );
  } catch {
    console.error(
      "Import annulé : vérifier le JSON, les champs et la connexion.",
    );
    process.exitCode = 1;
  } finally {
    await db.close();
  }
}
