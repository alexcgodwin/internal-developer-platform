import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from release_management.core import (Ledger, ReleaseError, desired_inventory, inventory,
                                     prepare, validate_request, read_json)


REQUEST = {
    "service": "guestbook-api", "environment": "dev", "version": "v1.2.3",
    "commit": "1234567890abcdef1234567890abcdef12345678",
    "image": "ghcr.io/example/guestbook-api@sha256:" + "a" * 64,
    "change_ref": "PR-123",
}


class ReleaseControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", "-b", "feature/release-demo", str(self.root)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.ledger = Ledger(self.root / ".local" / "release-tracking" / "observations.jsonl")

    def test_valid_request(self):
        self.assertEqual(validate_request(REQUEST), REQUEST)

    def test_rejects_invalid_service_and_path_traversal(self):
        for value in ["../credentials", "APP", "bad/name", ".hidden", "a--b"]:
            with self.subTest(value=value):
                with self.assertRaises(ReleaseError):
                    validate_request({**REQUEST, "service": value})

    def test_rejects_unpinned_image(self):
        with self.assertRaisesRegex(ReleaseError, "immutable"):
            validate_request({**REQUEST, "image": "ghcr.io/example/guestbook-api:latest"})

    def test_rejects_short_commit_and_unknown_fields(self):
        with self.assertRaises(ReleaseError):
            validate_request({**REQUEST, "commit": "deadbeef"})
        with self.assertRaises(ReleaseError):
            validate_request({**REQUEST, "shell": "rm -rf /"})

    def test_dry_run_does_not_write(self):
        response = prepare(self.root, REQUEST, preflight=False)
        self.assertFalse(response["written"])
        self.assertFalse((self.root / response["candidate"]).exists())

    def test_prepare_writes_intent_not_deployment(self):
        response = prepare(self.root, REQUEST, write=True, preflight=False)
        self.assertTrue(response["written"])
        self.assertEqual(desired_inventory(self.root)[("guestbook-api", "dev")], REQUEST)
        self.assertEqual(inventory(self.root, self.ledger)[0]["state"], "UNVERIFIED_NO_OBSERVATION")
        self.assertFalse(self.ledger.path.exists())

    def test_preflight_is_a_required_prepare_gate(self):
        from unittest.mock import patch
        with patch("release_management.core.run_preflight", return_value=["unit-tests", "diff-check"]) as preflight:
            result = prepare(self.root, REQUEST, preflight=True)
        preflight.assert_called_once_with(self.root)
        self.assertEqual(result["checks_run"], ["unit-tests", "diff-check"])

    def test_main_branch_blocked(self):
        subprocess.run(["git", "-C", str(self.root), "switch", "-q", "-c", "main"], check=True)
        with self.assertRaisesRegex(ReleaseError, "feature branch"):
            prepare(self.root, REQUEST, write=True, preflight=False)

    def test_production_blocked_without_explicit_override(self):
        req = {**REQUEST, "environment": "production"}
        with self.assertRaisesRegex(ReleaseError, "blocked"):
            prepare(self.root, req, write=True, preflight=False)
        self.assertFalse((self.root / "release_management" / "desired" / "production").exists())

    def test_production_override_only_writes_intent(self):
        req = {**REQUEST, "environment": "production"}
        output = prepare(self.root, req, write=True, allow_production=True, preflight=False)
        self.assertEqual(output["mode"], "PREPARE_ONLY_NO_DEPLOYMENT")
        self.assertTrue((self.root / output["candidate"]).exists())

    def test_existing_candidate_requires_review(self):
        prepare(self.root, REQUEST, write=True, preflight=False)
        changed = {**REQUEST, "version": "v2.0.0"}
        with self.assertRaisesRegex(ReleaseError, "--replace"):
            prepare(self.root, changed, write=True, preflight=False)
        self.assertEqual(read_json(self.root / "release_management/desired/dev/guestbook-api.json"), REQUEST)
        prepare(self.root, changed, write=True, preflight=False, replace=True)
        self.assertEqual(read_json(self.root / "release_management/desired/dev/guestbook-api.json")["version"], "v2.0.0")

    def test_successful_operator_observation_is_not_live_verified(self):
        prepare(self.root, REQUEST, write=True, preflight=False)
        self.ledger.append_observation(REQUEST, outcome="succeeded", evidence="https://example.com/deployments/12345", operator="tester")
        items = inventory(self.root, self.ledger)
        self.assertEqual(items[0]["state"], "MATCHES_OPERATOR_ASSERTION_NOT_LIVE_VERIFIED")
        self.assertEqual(len(self.ledger.read()), 1)

    def test_drift_detected(self):
        prepare(self.root, REQUEST, write=True, preflight=False)
        previous = {**REQUEST, "image": "ghcr.io/example/guestbook-api@sha256:" + "b" * 64}
        self.ledger.append_observation(previous, outcome="succeeded", evidence="https://example.com/deployments/12345", operator="tester")
        self.assertEqual(inventory(self.root, self.ledger)[0]["state"], "DRIFT_REPORTED")

    def test_failure_not_misreported_as_running(self):
        prepare(self.root, REQUEST, write=True, preflight=False)
        self.ledger.append_observation(REQUEST, outcome="failed", evidence="https://example.com/deployments/12345", operator="tester")
        self.assertEqual(inventory(self.root, self.ledger)[0]["state"], "FAILED_LAST_OBSERVATION")

    def test_tamper_detection(self):
        self.ledger.append_observation(REQUEST, outcome="succeeded", evidence="https://example.com/deployments/12345", operator="tester")
        text = self.ledger.path.read_text(encoding="utf-8")
        self.ledger.path.write_text(text.replace("succeeded", "failed"), encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "integrity"):
            self.ledger.read()

    def test_concurrent_writer_lock(self):
        self.ledger.path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.path.with_suffix(".jsonl.lock").touch()
        with self.assertRaisesRegex(ReleaseError, "locked"):
            self.ledger.append_observation(REQUEST, outcome="succeeded", evidence="https://example.com/deployments/12345", operator="tester")

    def test_invalid_operator_evidence_is_blocked(self):
        with self.assertRaisesRegex(ReleaseError, "HTTPS"):
            self.ledger.append_observation(REQUEST, outcome="succeeded", evidence="file:///local/log", operator="tester")

    def test_incomplete_ledger_line_fails_closed(self):
        self.ledger.path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.path.write_text('{"bad":true}', encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "incomplete"):
            self.ledger.read()


if __name__ == "__main__":
    unittest.main()
