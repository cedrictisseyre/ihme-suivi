import importlib.util
import io
import json
from pathlib import Path
import unittest
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("deploy_request", ROOT / "deploy/request.py")
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class DeploymentClient(unittest.TestCase):
    def test_http_failure_is_actionable_without_exposing_server_output(self):
        for payload, expected in [
            ({"error_code": "image_pull", "error": "secret"}, "Téléchargement impossible"),
            ({"error_code": ["secret"]}, "Échec HTTP 422"),
            ({"error": "secret"}, "Échec HTTP 422"),
        ]:
            with self.subTest(payload=payload):
                error = urllib.error.HTTPError(
                    "https://example.org/__deploy/p01", 422, "failure", {},
                    io.BytesIO(json.dumps(payload).encode()),
                )
                with patch.object(client.urllib.request, "build_opener") as opener:
                    opener.return_value.open.side_effect = error
                    with self.assertRaises(ValueError) as caught:
                        client.request_deployment(
                            "https://example.org/__deploy/p01", "token", "sha256:" + "a" * 64
                        )
                self.assertIn(expected, str(caught.exception))
                self.assertNotIn("secret", str(caught.exception))

    def test_student_template_matches_client(self):
        self.assertEqual(
            (ROOT / "deploy/request.py").read_bytes(),
            (ROOT / "docs/templates/student/deploy/request.py").read_bytes(),
        )
