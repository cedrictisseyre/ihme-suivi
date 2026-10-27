import { chromium } from "playwright-core";
import fs from "node:fs/promises";
import { allowsRequest } from "./policy.mjs";

let input = "";
for await (const chunk of process.stdin) {
  input += chunk;
  if (input.length > 65536) throw Error("Entrée trop volumineuse.");
}
const { origin, projects } = JSON.parse(input);
const address = new URL(origin);
if (
  address.protocol !== "https:" ||
  address.username ||
  address.password ||
  address.port ||
  address.pathname !== "/" ||
  address.search ||
  address.hash ||
  !Array.isArray(projects) ||
  projects.length > 99
)
  throw Error("Entrée invalide.");
for (const p of projects)
  if (
    !/^p[0-9]{2}$/.test(p.id) ||
    !/^sha256:[a-f0-9]{64}$/.test(p.digest) ||
    !/^\/[a-z0-9]+(?:-[a-z0-9]+)*\/$/.test(p.path)
  )
    throw Error("Projet invalide.");
await fs.mkdir("/tmp/home", { recursive: true });
const browser = await chromium.launch({
  headless: true,
  chromiumSandbox: true,
});
const results = [];
try {
  for (const project of projects) {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      deviceScaleFactor: 1,
      colorScheme: "light",
      reducedMotion: "reduce",
      serviceWorkers: "block",
      acceptDownloads: false,
    });
    // Un contexte neuf, sans cookie ni identifiant. La capture ne visite que l’espace public attribué.
    await context.route("**/*", (route) => {
      const request = route.request();
      return allowsRequest(
        address.origin,
        project.path,
        request.url(),
        request.method(),
        request.resourceType(),
      )
        ? route.continue()
        : route.abort();
    });
    await context.routeWebSocket("**/*", (socket) => socket.close());
    const page = await context.newPage();
    try {
      const response = await page.goto(origin + project.path, {
        waitUntil: "domcontentloaded",
        timeout: 20000,
      });
      if (!response || response.status() !== 200)
        throw Error("Application indisponible.");
      await page.evaluate(() =>
        Promise.race([
          document.fonts.ready,
          new Promise((resolve) => setTimeout(resolve, 1500)),
        ]),
      );
      await page.waitForTimeout(1500);
      if (!page.url().startsWith(origin + project.path))
        throw Error("Redirection interdite.");
      if (
        !(await page.locator("body").innerText()).trim() &&
        !(await page.locator("body img,body canvas,body svg").count())
      )
        throw Error("Page vide.");
      const filename = project.id + "-" + project.digest.slice(7) + ".jpg";
      await page.screenshot({
        path: "/output/" + filename,
        type: "jpeg",
        quality: 72,
        fullPage: false,
        animations: "disabled",
        caret: "hide",
        timeout: 10000,
      });
      results.push({ id: project.id, filename, status: "ok" });
    } catch {
      results.push({ id: project.id, status: "unavailable" });
    } finally {
      await context.close();
    }
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify(results));
