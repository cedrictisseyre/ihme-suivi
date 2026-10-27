import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

PLATFORM = Path(__file__).parents[1] / "deploy/platform"
sys.path.insert(0, str(PLATFORM))
try:
    spec = importlib.util.spec_from_file_location("update_gallery", PLATFORM / "update-gallery.py")
    gallery_export = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gallery_export)
finally:
    sys.path.pop(0)


class GalleryExport(unittest.TestCase):
    def test_projection_atomic_files_and_readable_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assignments = root / "etc/ihme-gallery"
            assignments.mkdir(parents=True)
            (root / "opt/ihme-platform").mkdir(parents=True)
            project = {"id": "p01", "slug": "durees", "title": "Durées fictives", "repository": "https://github.com/demo/durees", "token": "PRIVATE_TOKEN"}
            (assignments / "projects.json").write_text(json.dumps([project]))
            exported = {
                "rows": [{"repository_url": project["repository"], "student_name": "Démo", "daily_activity": None}],
                "reports": [{"repository_url": project["repository"], "progression": {
                    "milestones": [{"position": 1, "status": "doing", "title": "Cadrage", "expected": "Un besoin", "demonstration": "Expliquer", "next": "Compléter le README"}],
                    "reviews": [], "criteria": [], "private_note": "PRIVATE_NOTE",
                }}],
            }

            def local_path(value):
                value = str(value)
                if value.startswith("/etc/ihme-gallery") or value.startswith("/opt/ihme-platform"):
                    return root / value.lstrip("/")
                return Path(value)

            old_mask = os.umask(0o022)
            try:
                with patch.object(gallery_export, "Path", side_effect=local_path), patch.object(gallery_export.subprocess, "check_output", return_value=json.dumps(exported)), patch.object(gallery_export, "deployments", return_value={}):
                    gallery_export.update()
            finally:
                os.umask(old_mask)
            platform = root / "opt/ihme-platform"
            index = json.loads((platform / "teacher-sites/projects.json").read_text())
            self.assertEqual(set(index[0]), {"id", "repository", "slug"})
            public = platform / "public"
            self.assertIn('/progression/p01/', (public / "index.html").read_text())
            page = (public / "progression/p01/index.html").read_text()
            self.assertIn("Compléter le README", page)
            self.assertNotIn("PRIVATE_TOKEN", page)
            self.assertNotIn("PRIVATE_NOTE", page)
            for directory in [platform / "teacher-sites", public, public / "progression", public / "progression/p01"]:
                self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o755)
            self.assertEqual(stat.S_IMODE((public / "progression/p01/index.html").stat().st_mode), 0o644)
            self.assertFalse(list(public.rglob("*.tmp")))
