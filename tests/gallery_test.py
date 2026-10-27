import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "gallery", Path(__file__).parents[1] / "deploy/platform/gallery.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Gallery(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "id": "p01",
                "slug": "score-center",
                "title": "<Projet>",
                "student_name": "Étudiant <Démo>",
                "email": "ADRESSE_PRIVEE",
                "token": "JETON_PRIVE",
                "repository": "DEPOT_PRIVE",
            }
        ]

    def test_requested_names_are_escaped_but_secrets_and_addresses_stay_private(self):
        result = module.render_gallery(self.rows)
        self.assertIn("&lt;Projet&gt;", result)
        self.assertIn("Étudiant &lt;Démo&gt;", result)
        for value in ["ADRESSE_PRIVEE", "JETON_PRIVE", "DEPOT_PRIVE"]:
            self.assertNotIn(value, result)

    def test_teacher_requires_a_different_origin(self):
        with self.assertRaises(ValueError):
            module.render_caddy("cours.example.fr", "cours.example.fr", self.rows)

    def test_path_router_and_pending_page(self):
        result = module.render_caddy(
            "suivi.example.fr", "projets.example.fr", self.rows
        )
        self.assertIn("handle_path /score-center/*", result)
        self.assertIn("reverse_proxy p01:3000", result)
        self.assertIn("handle_errors", result)
        self.assertIn("rewrite * /_unavailable.html", result)
        self.assertIn("status 503", result)
        self.assertIn('id="theme-toggle"', module.render_pending())
        self.assertIn("ihme-gallery-theme", module.render_pending())

    def test_chart_is_numeric_only_and_unavailable_is_not_zero(self):
        days = [
            {"date": "2026-10-" + str(i).zfill(2), "count": 1 if i == 26 else 0}
            for i in range(13, 27)
        ]
        result = module.render_gallery(
            self.rows,
            {
                "p01": {
                    "days": days,
                    "complete": True,
                    "observation": "OBSERVATION_PRIVEE",
                    "token": "JETON_PRIVE",
                }
            },
        )
        self.assertEqual(result.count("<rect "), 14)
        self.assertIn("26/10 : 1 commits", result)
        self.assertNotIn("OBSERVATION_PRIVEE", result)
        self.assertNotIn("JETON_PRIVE", result)
        self.assertIn("données indisponibles", module.render_chart(None))
        self.assertNotIn("<svg", module.render_chart(None))
        self.assertIn(
            "lecture partielle", module.render_chart({"days": days, "complete": False})
        )

    def test_previews_only_use_valid_local_images_for_published_projects(self):
        image = "/previews/p01-" + "a" * 64 + ".jpg"
        data = {"p01": {"published": True, "available": True, "thumbnail": image}}
        result = module.render_gallery(self.rows, deployments=data)
        self.assertIn('class="project-preview"', result)
        self.assertIn(image, result)
        self.assertIn('loading="lazy"', result)
        self.assertIn("En ligne", result)
        data["p01"]["thumbnail"] = "https://external.invalid/image.jpg"
        result = module.render_gallery(self.rows, deployments=data)
        self.assertNotIn("<img", result)
        self.assertIn("Aperçu en préparation", result)
        self.assertNotIn("<img", module.render_gallery(self.rows))

    def test_path_cannot_inject_caddy_configuration(self):
        self.rows[0]["slug"] = "x/../__deploy"
        with self.assertRaises(ValueError):
            module.render_gallery(self.rows)


if __name__ == "__main__":
    unittest.main()
