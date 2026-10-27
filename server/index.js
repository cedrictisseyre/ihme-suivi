import { createDatabase } from "./db.js";
import { createApp } from "./app.js";
const db = createDatabase(process.env.DATABASE_URL);
const secure = process.env.COOKIE_SECURE !== "false";
if (
  !process.env.PUBLIC_ORIGIN ||
  (secure && !process.env.PUBLIC_ORIGIN.startsWith("https://"))
)
  throw new Error("PUBLIC_ORIGIN HTTPS obligatoire en production.");
const app = createApp(db, {
  password: process.env.ADMIN_PASSWORD,
  origin: process.env.PUBLIC_ORIGIN,
  secure,
  version: process.env.APP_VERSION,
  studentOrigin: process.env.STUDENT_ORIGIN,
  githubToken: process.env.GITHUB_TOKEN,
  gitlabToken: process.env.GITLAB_TOKEN,
});
const server = app.listen(Number(process.env.PORT || 3000), "0.0.0.0", () =>
  console.log("IHME écoute sur le port 3000."),
);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => {
    server.close(async () => {
      await db.close();
      process.exit(0);
    });
    setTimeout(() => process.exit(1), 10000).unref();
  });
