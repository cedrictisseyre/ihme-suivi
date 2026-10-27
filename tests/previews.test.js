import { test } from "node:test";
import assert from "node:assert/strict";
import { allowsRequest } from "../deploy/previews/policy.mjs";
const origin = "https://projets.example.fr",
  path = "/demo/";
test("miniatures : ressources du projet autorisées, autre projet et routes privées refusés", () => {
  assert.equal(
    allowsRequest(
      origin,
      path,
      origin + "/demo/assets/main.js",
      "GET",
      "script",
    ),
    true,
  );
  for (const url of [
    origin + "/__deploy/p01",
    origin + "/autre/api",
    origin + "/demonstration/",
    "https://suivi.example.fr/api/projects",
    "http://127.0.0.1:3000",
    "https://169.254.169.254/latest",
    "https://user:password@projets.example.fr/demo/",
  ])
    assert.equal(
      allowsRequest(origin, path, url, "GET", "document"),
      false,
      url,
    );
});
test("miniatures : aucune écriture HTTP ni requête arbitraire vers un CDN", () => {
  for (const method of ["POST", "PUT", "PATCH", "DELETE"])
    assert.equal(
      allowsRequest(origin, path, origin + "/demo/api", method, "fetch"),
      false,
    );
  assert.equal(
    allowsRequest(
      origin,
      path,
      "https://fonts.gstatic.com/font.woff",
      "GET",
      "font",
    ),
    true,
  );
  assert.equal(
    allowsRequest(
      origin,
      path,
      "https://unpkg.com/package.js",
      "GET",
      "script",
    ),
    true,
  );
  assert.equal(
    allowsRequest(origin, path, "https://unpkg.com/private", "GET", "fetch"),
    false,
  );
});
