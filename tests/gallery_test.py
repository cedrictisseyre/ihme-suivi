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

    def test_public_progress_menu_and_safe_read_only_page(self):
        report = {
            "generated_at": "2026-10-27T12:00:00Z",
            "sha": "a" * 40,
            "stale": True,
            "milestones": [{
                "position": 1, "title": "Cadrage", "status": "done", "teacher": True,
                "expected": "Un scénario STAPS", "demonstration": "Expliquer",
                "public_note": "<script>alert(1)</script>",
                "evidence": "OBSERVATION_PRIVEE", "next": "Tester",
            }],
            "criteria": [{"key": "functionality", "title": "Fonctionnement", "max": 6, "anchors": "Repères"}],
            "assessment": {"scores": [{"key": "functionality", "value": 0}], "comment": "À poursuivre"},
            "reviews": [{"date": "2026-10-27", "achievements": "Calcul expliqué", "next_step": "Vérifier le cas vide", "assistance": "AIDE_PRIVEE"}],
            "history": [{"sha": "a" * 40, "observed": 0, "generated_at": "2026-10-27T12:00:00Z"}],
            "token": "JETON_PRIVE",
        }
        gallery = module.render_gallery(self.rows, progression={"p01": report})
        self.assertIn('href="/progression/p01/"', gallery)
        self.assertIn("1/6 jalons validés", gallery)
        self.assertIn("Menu du projet P1", gallery)
        page = module.render_progress(self.rows[0], report)
        for value in ["OBSERVATION_PRIVEE", "AIDE_PRIVEE", "JETON_PRIVE", "ADRESSE_PRIVEE", "DEPOT_PRIVE"]:
            self.assertNotIn(value, page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("Calcul expliqué", page)
        self.assertIn("Vérifier le cas vide", page)
        self.assertIn("0/6", page)
        self.assertIn("13:00", page)
        self.assertNotIn("<form", page)
        caddy = module.render_caddy("suivi.example.fr", "projets.example.fr", self.rows)
        self.assertIn("handle /progression/*", caddy)
        self.assertIn("Bilan à préparer", module.render_progress(self.rows[0]))
        self.rows[0]["slug"] = "progression"
        with self.assertRaises(ValueError):
            module.checked_rows(self.rows)

    def test_path_cannot_inject_caddy_configuration(self):
        self.rows[0]["slug"] = "x/../__deploy"
        with self.assertRaises(ValueError):
            module.render_gallery(self.rows)


if __name__ == "__main__":
    unittest.main()
