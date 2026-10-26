import pg from "pg";
import fs from "node:fs/promises";
export function createDatabase(url) {
  if (!url) throw new Error("DATABASE_URL est obligatoire.");
  const pool = new pg.Pool({
    connectionString: url,
    max: 8,
    connectionTimeoutMillis: 5000,
  });
  pool.on("error", () => console.error("Connexion PostgreSQL interrompue."));
  return {
    query: (sql, values) => pool.query(sql, values),
    async transaction(fn) {
      const c = await pool.connect();
      try {
        await c.query("BEGIN");
        const result = await fn(c);
        await c.query("COMMIT");
        return result;
      } catch (err) {
        await c.query("ROLLBACK");
        throw err;
      } finally {
        c.release();
      }
    },
    close: () => pool.end(),
  };
}
export async function migrate(db) {
  const schema = await fs.readFile(
    new URL("./schema.sql", import.meta.url),
    "utf8",
  );
  await db.transaction(async (c) => {
    await c.query("SELECT pg_advisory_xact_lock(7261041)");
    // Migration additive et idempotente, à exécuter avant le lancement de l’API.
    for (const statement of schema.split(";").filter((s) => s.trim()))
      await c.query(statement);
  });
}
