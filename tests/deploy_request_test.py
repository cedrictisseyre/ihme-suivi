import importlib.util
import io
import json
from pathlib import Path
import unittest
import urllib.error
from unittest.mock import patch, MagicMock

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

    def test_busy_responses_are_retried_with_same_digest_without_leaking_tokens(self):
        digest = "sha256:" + "a" * 64
        result = {"status": "healthy", "project": "p01", "digest": digest}
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = json.dumps(result).encode()
        errors = [urllib.error.HTTPError("https://example.org/__deploy/p01", code, "busy", {"Retry-After": "5"}, io.BytesIO(b'{}')) for code in (409, 429)]
        with patch.object(client.urllib.request, "build_opener") as opener, patch.object(client.time, "sleep") as sleep, patch("sys.stdout", new_callable=io.StringIO) as output:
            opener.return_value.open.side_effect = errors + [response]
            self.assertEqual(client.request_deployment("https://example.org/__deploy/p01", "PRIVATE_TOKEN", digest, "PRIVATE_REGISTRY"), result)
            self.assertEqual(opener.return_value.open.call_count, 3)
            self.assertEqual(sleep.call_count, 2)
            self.assertNotIn("PRIVATE", output.getvalue())
            for call in opener.return_value.open.call_args_list:
                self.assertEqual(json.loads(call.args[0].data)["digest"], digest)

    def test_busy_retry_count_is_bounded(self):
        errors = [urllib.error.HTTPError("https://example.org/__deploy/p01", 409, "busy", {"Retry-After": "invalid"}, io.BytesIO(b'{}')) for _ in range(12)]
        with patch.object(client.urllib.request, "build_opener") as opener, patch.object(client.time, "sleep") as sleep, patch("sys.stdout", new_callable=io.StringIO):
            opener.return_value.open.side_effect = errors
            with self.assertRaisesRegex(ValueError, "12 tentatives"):
                client.request_deployment("https://example.org/__deploy/p01", "token", "sha256:" + "a" * 64)
            self.assertEqual(opener.return_value.open.call_count, 12)
            self.assertEqual(sleep.call_count, 11)

    def test_network_timeout_is_not_replayed(self):
        with patch.object(client.urllib.request, "build_opener") as opener, patch.object(client.time, "sleep") as sleep:
            opener.return_value.open.side_effect = TimeoutError()
            with self.assertRaises(TimeoutError):
                client.request_deployment("https://example.org/__deploy/p01", "token", "sha256:" + "a" * 64)
            self.assertEqual(opener.return_value.open.call_count, 1)
            sleep.assert_not_called()

    def test_student_template_matches_client(self):
        self.assertEqual(
            (ROOT / "deploy/request.py").read_bytes(),
            (ROOT / "docs/templates/student/deploy/request.py").read_bytes(),
        )
