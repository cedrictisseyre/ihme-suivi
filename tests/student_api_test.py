import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "student_api", Path(__file__).parents[1] / "deploy/students/api.py"
)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class DeployAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.original_base = api.BASE
        cls.original_teacher_base = api.TEACHER_BASE
        api.BASE = Path(cls.tmp.name)
        project = api.BASE / "p01"
        project.mkdir()
        (project / ".deploy-token.sha256").write_text(
            hashlib.sha256(b"fixture-token").hexdigest()
        )
        api.TEACHER_BASE = api.BASE / "teacher"
        api.TEACHER_BASE.mkdir()
        (api.TEACHER_BASE / ".deploy-token.sha256").write_text(
            hashlib.sha256(b"teacher-fixture").hexdigest()
        )
        cls.path = str(api.BASE / "test.sock")
        cls.server = api.Server(cls.path, api.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        api.BASE = cls.original_base
        api.TEACHER_BASE = cls.original_teacher_base
        cls.tmp.cleanup()

    def call(self, project="p01", token="fixture-token", data=None):
        client = http.client.HTTPConnection("localhost")

        def connect():
            client.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.sock.connect(self.path)

        client.connect = connect
        body = json.dumps(
            data if data is not None else {"digest": "sha256:" + "a" * 64}
        )
        client.request(
            "POST",
            "/__deploy/" + project,
            body=body,
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
            },
        )
        response = client.getresponse()
        result = response.status, json.loads(response.read())
        client.close()
        return result

    def test_token_cannot_deploy_another_project(self):
        self.assertEqual(self.call(project="p02")[0], 401)
        self.assertEqual(self.call(token="incorrect")[0], 401)

    def test_teacher_has_a_separate_token_and_fixed_command(self):
        self.assertEqual(self.call(project="suivi")[0], 401)
        self.assertEqual(self.call(token="teacher-fixture")[0], 401)
        with patch.object(api.subprocess, "run") as execute:
            execute.return_value.returncode = 0
            self.assertEqual(
                self.call(project="suivi", token="teacher-fixture")[0], 200
            )
            self.assertEqual(execute.call_args.args[0], [api.TEACHER_EXECUTABLE])

    def test_registry_token_is_transient_and_not_a_command_argument(self):
        with patch.object(api.subprocess, "run") as execute:
            execute.return_value.returncode = 0
            data = {
                "digest": "sha256:" + "a" * 64,
                "registry_token": "ephemeral-fixture",
            }
            self.assertEqual(self.call(data=data)[0], 200)
            self.assertEqual(
                execute.call_args.kwargs["env"]["IHME_REGISTRY_TOKEN"],
                "ephemeral-fixture",
            )
            self.assertNotIn("ephemeral-fixture", str(execute.call_args.args))
            self.assertEqual(
                self.call(data={**data, "registry_token": "bad\nvalue"})[0], 400
            )

    def test_bad_digest_or_extra_options_never_execute(self):
        with patch.object(api.subprocess, "run") as execute:
            self.assertEqual(self.call(data={"digest": "latest"})[0], 400)
            self.assertEqual(
                self.call(data={"digest": "sha256:" + "a" * 64, "privileged": True})[0],
                400,
            )
            execute.assert_not_called()

    def test_valid_request_runs_only_the_fixed_project_command(self):
        with patch.object(api.subprocess, "run") as execute:
            execute.return_value.returncode = 0
            self.assertEqual(self.call()[0], 200)
            self.assertEqual(execute.call_args.args[0], [api.EXECUTABLE, "p01"])
            self.assertEqual(
                execute.call_args.kwargs["input"], "sha256:" + "a" * 64 + "\n"
            )

    def test_failure_exposes_only_allowlisted_code(self):
        with patch.object(api.subprocess, "run") as execute:
            execute.return_value.returncode = 1
            execute.return_value.stderr = "DEPLOY_ERROR:image_pull\n"
            status, data = self.call()
            self.assertEqual(status, 422)
            self.assertEqual(data["error_code"], "image_pull")
            execute.return_value.stderr = "private registry token or database URL"
            status, data = self.call()
            self.assertEqual(data["error_code"], "deployment_failed")
            self.assertNotIn("private", json.dumps(data))

    def test_concurrent_deployment_is_refused(self):
        with api.GATE:
            self.assertEqual(self.call()[0], 409)


if __name__ == "__main__":
    unittest.main()
