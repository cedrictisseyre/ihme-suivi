import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "student_deploy", Path(__file__).parents[1] / "deploy/students/deploy.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RequestValidation(unittest.TestCase):
    def test_fixed_identity_and_immutable_digest(self):
        module.validate_request("p01", "sha256:" + "a" * 64)

    def test_no_implicit_image_volumes(self):
        module.validate_image_config({"Volumes": None})
        module.validate_image_config({"Volumes": {}})
        with self.assertRaises(ValueError):
            module.validate_image_config({"Volumes": {"/data": {}}})

    def test_no_path_traversal_or_shell_arguments(self):
        for project in ["../p01", "p01;id", "p001", "root", "--privileged"]:
            with self.subTest(project=project), self.assertRaises(ValueError):
                module.validate_request(project, "sha256:" + "a" * 64)

    def test_no_image_replacement_tags_or_docker_options(self):
        for digest in [
            "latest",
            "ghcr.io/autre/image:latest",
            "sha256:" + "a" * 63,
            "sha256:" + "a" * 64 + " --privileged",
            "sha256:" + "A" * 64,
        ]:
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                module.validate_request("p01", digest)


if __name__ == "__main__":
    unittest.main()
