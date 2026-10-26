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
        api.BASE = Path(cls.tmp.name)
        project = api.BASE / "p01"
        project.mkdir()
        (project / ".deploy-token.sha256").write_text(
            hashlib.sha256(b"fixture-token").hexdigest()
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

    def test_concurrent_deployment_is_refused(self):
        with api.GATE:
            self.assertEqual(self.call()[0], 409)


if __name__ == "__main__":
    unittest.main()
