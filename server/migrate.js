import { createDatabase, migrate } from "./db.js";
const db = createDatabase(process.env.DATABASE_URL);
try {
  await migrate(db);
  console.log("Schéma PostgreSQL prêt.");
} catch {
  console.error(
    "Migration impossible : vérifier la connexion et les droits PostgreSQL.",
  );
  process.exitCode = 1;
} finally {
  await db.close();
}
