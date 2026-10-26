import { createDatabase } from "./db.js";
import { MILESTONES } from "./domain.js";
export async function seed(db) {
  await db.transaction(async (c) => {
    await c.query("SELECT pg_advisory_xact_lock(7261041)");
    if ((await c.query("SELECT id FROM projects LIMIT 1")).rows.length) return;
    for (const [i, title] of [
      "Atelier des objets",
      "Carnet de lectures",
      "Potager connecté",
      "Échappées culturelles",
    ].entries()) {
      const { id } = (
        await c.query(
          "INSERT INTO projects(student_name,title,objective) VALUES($1,$2,$3) RETURNING id",
          [
            `Étudiant démo ${i + 1}`,
            title,
            "Concevoir une application accessible avec React, Express et PostgreSQL.",
          ],
        )
      ).rows[0];
      for (const [j, m] of MILESTONES.entries())
        await c.query(
          "INSERT INTO milestones(project_id,position,title,status,due_date) VALUES($1,$2,$3,$4,$5)",
          [
            id,
            j + 1,
            m,
            j < i + 1
              ? "done"
              : j === i + 1
                ? i === 1
                  ? "blocked"
                  : "doing"
                : "todo",
            `2026-11-${String(2 + j * 4).padStart(2, "0")}`,
          ],
        );
      await c.query(
        "INSERT INTO reviews(project_id,reviewed_on,commit_ref,achievements,blocker,next_step) VALUES($1,$2,$3,$4,$5,$6)",
        [
          id,
          "2026-10-26",
          "a1b2c3d",
          "Le besoin et les premiers parcours sont présentés.",
          i === 1 ? "Relation entre livres et collections à clarifier." : "",
          "Ajouter un test du prochain parcours.",
        ],
      );
    }
  });
}
if (process.argv[1]?.endsWith("/seed.js")) {
  const db = createDatabase(process.env.DATABASE_URL);
  try {
    await seed(db);
    console.log("Démonstration prête (base vide uniquement).");
  } finally {
    await db.close();
  }
}
