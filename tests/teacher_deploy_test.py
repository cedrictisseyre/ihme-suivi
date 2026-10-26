import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "teacher_deploy", Path(__file__).parents[1] / "deploy/teacher/deploy.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TeacherDeploy(unittest.TestCase):
    def test_only_immutable_digests_are_accepted(self):
        module.validate_digest("sha256:" + "a" * 64)
        for digest in [
            "latest",
            "ghcr.io/other/image:latest",
            "sha256:" + "a" * 64 + ";id",
        ]:
            with self.assertRaises(ValueError):
                module.validate_digest(digest)

    def test_config_update_preserves_secrets_and_database(self):
        original = "ADMIN_PASSWORD=private-fixture\nDATABASE_URL=postgresql://fixture\nAPP_IMAGE=old\nAPP_VERSION=old\n"
        updated = module.updated_config(
            original, "ghcr.io/demo/app@sha256:fixture", "revision"
        )
        self.assertIn("ADMIN_PASSWORD=private-fixture\n", updated)
        self.assertIn("DATABASE_URL=postgresql://fixture\n", updated)
        self.assertEqual(updated.count("APP_IMAGE="), 1)
        self.assertNotIn("APP_IMAGE=old", updated)


if __name__ == "__main__":
    unittest.main()
