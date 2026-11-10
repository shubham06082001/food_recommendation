import json
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote_plus

import services


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.root_patch = patch.object(services, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_running_services_never_call_docker(self):
        with patch.object(services, "listening", return_value=True), patch.object(services, "docker") as docker:
            for service in services.SERVICES:
                services.ensure_service(*service)
            docker.assert_not_called()

    def test_stopped_container_is_reused(self):
        container = {"Id": "existing", "Name": "/mongo-prod-local", "HostConfig": {
            "PortBindings": {"27017/tcp": [{"HostPort": "20000"}]}}}
        with patch.object(services, "listening", side_effect=[False, True]), patch.object(
            services, "docker", side_effect=["existing", json.dumps([container]), "existing"]
        ) as docker:
            services.ensure_service(*services.SERVICES[0])
            self.assertEqual(docker.call_args.args, ("start", "existing"))
            self.assertNotIn("run", [call.args[0] for call in docker.call_args_list])

    def test_absent_services_get_persistent_storage(self):
        for service in services.SERVICES:
            with self.subTest(service=service[0]), patch.object(
                services, "listening", side_effect=[False, True]
            ), patch.object(services, "docker", side_effect=["", "created"]) as docker:
                services.ensure_service(*service)
                arguments = docker.call_args.args
                self.assertEqual(arguments[:2], ("run", "-d"))
                self.assertIn("unless-stopped", arguments)
                self.assertIn(f"{service[1]}:{service[2]}", arguments)
                self.assertIn(f"ecos-{service[0]}-data:{service[4]}", arguments)
                self.assertNotIn("--rm", arguments)

    def test_check_mode_never_starts_missing_services(self):
        with patch.object(services, "listening", return_value=False), patch.object(services, "docker") as docker:
            with self.assertRaises(RuntimeError):
                services.ensure_service(*services.SERVICES[0], check_only=True)
            docker.assert_not_called()

    def test_existing_collections_are_never_uploaded(self):
        with patch.object(services, "qdrant_request", side_effect=[
            {"collections": [{"name": "food_nutrients"}, {"name": "ecos_ingredients"}]},
            {"status": "green", "points_count": 1014}, {"status": "green", "points_count": 38},
        ]), patch.object(services, "upload_snapshot") as upload:
            services.restore_snapshots()
            upload.assert_not_called()

    def test_missing_collection_is_uploaded_with_valid_multipart(self):
        snapshots = self.root / "qdrant-snapshot"
        snapshots.mkdir()
        contents = b"binary-snapshot\x00\xff" * 100000
        (snapshots / "food_nutrients-123-2026-11-05.snapshot").write_bytes(contents)

        def request(path, data=None, headers=None):
            if path == "/collections":
                return {"collections": [{"name": "ecos_ingredients"}]}
            if "/snapshots/upload" in path:
                body = b"".join(data)
                self.assertEqual(len(body), int(headers["Content-Length"]))
                self.assertIn(contents, body)
                self.assertIn("wait=true&priority=snapshot", path)
                self.assertTrue(body.endswith(b"--\r\n"))
                return True
            return {"status": "green", "points_count": 10}

        with patch.object(services, "qdrant_request", side_effect=request) as request_mock:
            services.restore_snapshots()
            uploads = [call for call in request_mock.call_args_list if "/snapshots/upload" in call.args[0]]
            self.assertEqual(len(uploads), 1)

    def test_missing_snapshot_fails_without_creating_collection(self):
        with patch.object(services, "qdrant_request", return_value={"collections": []}) as request:
            with self.assertRaisesRegex(RuntimeError, "No snapshot supplied"):
                services.restore_snapshots()
            self.assertEqual(request.call_count, 1)

    def test_empty_existing_collection_fails_without_overwriting(self):
        with patch.object(services, "qdrant_request", side_effect=[
            {"collections": [{"name": "food_nutrients"}]}, {"status": "green", "points_count": 0},
        ]), patch.object(services, "upload_snapshot") as upload:
            with self.assertRaisesRegex(RuntimeError, "empty"):
                services.restore_snapshots()
            upload.assert_not_called()

    def test_config_preserves_credentials_and_other_secrets(self):
        (self.root / ".env").write_text(
            "ECOS_MONGODB_URI=mongodb://alice:secret@localhost:20000/?authSource=admin\n"
            "ECOS_MANAGER_PASSWORD=keep-this-password\nOPENAI_API_KEY=keep-this-key\n")
        services.configure_env()
        first = (self.root / ".env").read_text()
        self.assertIn("mongodb://alice:secret@host.docker.internal:20000/?authSource=admin", first)
        self.assertIn("ECOS_MANAGER_PASSWORD=keep-this-password", first)
        self.assertIn("OPENAI_API_KEY=keep-this-key", first)
        services.configure_env()
        self.assertEqual(first, (self.root / ".env").read_text())

    def test_legacy_credentials_are_preserved(self):
        password = secrets.token_urlsafe(12) + "@"
        (self.root / ".env").write_text(f"DB_USERNAME=alice\nDB_PASSWORD={password}\n")
        services.configure_env()
        self.assertIn(f"mongodb://alice:{quote_plus(password)}@host.docker.internal:20000",
                      (self.root / ".env").read_text())

    def test_fresh_env_generates_password_and_urls(self):
        (self.root / "env.template").write_text("ECOS_MANAGER_PASSWORD=CHANGE_ME_min_8_chars\n")
        services.configure_env()
        result = (self.root / ".env").read_text()
        self.assertNotIn("CHANGE_ME", result)
        self.assertIn("QDRANT_VECTOR_DB_URL=http://host.docker.internal:6333", result)
        self.assertIn("ECOS_MONGODB_URI=mongodb://host.docker.internal:20000", result)


if __name__ == "__main__":
    unittest.main()