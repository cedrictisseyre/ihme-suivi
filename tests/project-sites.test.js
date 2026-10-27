import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile, mkdir, rm, utimes } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import request from "supertest";
import { projectSite } from "../server/project-sites.js";
import { createApp } from "../server/app.js";

test("site étudiant : numéro provisionné, lien et dernière capture du bon projet", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "ihme-sites-"));
  try {
    const config = {
      galleryProjectsPath: path.join(folder, "projects.json"),
      previewsPath: path.join(folder, "previews"),
      studentOrigin: "https://students.example.org",
    };
    await mkdir(config.previewsPath);
    await writeFile(
      config.galleryProjectsPath,
      JSON.stringify([
        {
          id: "p20",
          repository: "https://github.com/student/project",
          slug: "mon-site",
        },
      ]),
    );
    const old = `p20-${"a".repeat(64)}.jpg`;
    const recent = `p20-${"b".repeat(64)}.jpg`;
    await writeFile(path.join(config.previewsPath, old), "old");
    await utimes(path.join(config.previewsPath, old), 1, 1);
    await writeFile(path.join(config.previewsPath, recent), "image");
    await writeFile(
      path.join(config.previewsPath, `p01-${"c".repeat(64)}.jpg`),
      "other",
    );
    const site = await projectSite(
      { id: 1, repository_url: "https://github.com/Student/Project.git/" },
      config,
    );
    assert.deepEqual(site, {
      id: "p20",
      label: "P20",
      url: "https://students.example.org/mon-site/",
      thumbnail: `/api/project-previews/${recent}`,
      progress_url: "https://students.example.org/progression/p20/",
    });
    assert.equal(
      await projectSite(
        { id: 20, repository_url: "https://github.com/other/project" },
        config,
      ),
      null,
    );

    const app = createApp(
      { query: async () => ({ rows: [{}] }) },
      {
        ...config,
        password: "long-enough-test-password",
        secure: false,
      },
    );
    await request(app).get(site.thumbnail).expect(401);
    const response = await request(app)
      .get(site.thumbnail)
      .set("Cookie", "ihme_session=fixture")
      .expect(200);
    assert.match(response.headers["content-type"], /image\/jpeg/);
    await request(app)
      .get("/api/project-previews/projects.json")
      .set("Cookie", "ihme_session=fixture")
      .expect(404);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
});

test("site étudiant : configuration absente et capture encore indisponible", async () => {
  const folder = await mkdtemp(path.join(os.tmpdir(), "ihme-sites-"));
  try {
    const config = {
      galleryProjectsPath: path.join(folder, "projects.json"),
      previewsPath: folder,
    };
    const project = {
      repository_url: "https://github.com/a/b",
      deployed_url: "https://example.org/site/",
    };
    assert.equal(await projectSite(project, config), null);
    await writeFile(
      config.galleryProjectsPath,
      JSON.stringify([{ id: "p01", repository: project.repository_url }]),
    );
    assert.deepEqual(await projectSite(project, config), {
      id: "p01",
      label: "P1",
      url: project.deployed_url,
      thumbnail: null,
      progress_url: null,
    });
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
});
