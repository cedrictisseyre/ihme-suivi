import { PGlite } from "@electric-sql/pglite";
import { migrate } from "./db.js";
import { seed } from "./seed.js";
import { createApp } from "./app.js";
const pg = new PGlite(".demo-data");
const db = {
  query: (...args) => pg.query(...args),
  transaction: (fn) => pg.transaction(fn),
};
await migrate(db);
await seed(db);
createApp(db, {
  password: "Demonstration-IHME-2026!",
  origin: "http://localhost:3000",
  secure: false,
  version: "demo-embedded",
}).listen(3000, "127.0.0.1", () =>
  console.log(
    "Démo fictive http://localhost:3000 — mot de passe dans .env.example.",
  ),
);
