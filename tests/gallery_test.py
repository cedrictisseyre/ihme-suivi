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
                "student_name": "PERSONNE_PRIVEE",
                "token": "JETON_PRIVE",
                "repository": "DEPOT_PRIVE",
            }
        ]

    def test_only_project_titles_are_public_and_escaped(self):
        result = module.render_gallery(self.rows)
        self.assertIn("&lt;Projet&gt;", result)
        for value in ["PERSONNE_PRIVEE", "JETON_PRIVE", "DEPOT_PRIVE"]:
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
        self.assertIn("` 503", result)

    def test_path_cannot_inject_caddy_configuration(self):
        self.rows[0]["slug"] = "x/../__deploy"
        with self.assertRaises(ValueError):
            module.render_gallery(self.rows)


if __name__ == "__main__":
    unittest.main()
