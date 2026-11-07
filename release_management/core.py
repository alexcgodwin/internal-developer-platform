"""Offline release intent, observed-state ledger and deterministic release preparation.

Never contacts GitHub, Kubernetes, a container registry or an AI API.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENVIRONMENTS = frozenset({"dev", "staging", "production"})
SERVICE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^v?\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$")
COMMIT_PATTERN = re.compile(r"^[a-fA-F0-9]{40}$")
IMAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[a-fA-F0-9]{64}$")
EXPECTED_KEYS = {"service", "environment", "version", "commit", "image", "change_ref"}


class ReleaseError(ValueError):
    """Invalid or unsafe release request."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def digest(payload: Any) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


def read_json(path: Path) -> dict:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseError(f"Cannot read JSON at {path}: {exc}") from exc
    if not isinstance(content, dict):
        raise ReleaseError("Expected a JSON object")
    return content


def validate_request(value: dict) -> dict:
    if set(value) != EXPECTED_KEYS:
        raise ReleaseError(f"Request fields must be exactly {', '.join(sorted(EXPECTED_KEYS))}")
    if not all(isinstance(v, str) and v.strip() == v for v in value.values()):
        raise ReleaseError("All request fields must be nonempty strings without surrounding whitespace")
    service, env = value["service"], value["environment"]
    if not SERVICE_PATTERN.fullmatch(service) or len(service) > 63:
        raise ReleaseError("Invalid service name; use lower-case DNS label syntax")
    if env not in ENVIRONMENTS:
        raise ReleaseError("Environment must be dev, staging, or production")
    if not VERSION_PATTERN.fullmatch(value["version"]):
        raise ReleaseError("Version must be a semantic version, e.g. v1.2.3")
    if not COMMIT_PATTERN.fullmatch(value["commit"]):
        raise ReleaseError("Commit must be a complete 40-character Git SHA-1")
    if not IMAGE_PATTERN.fullmatch(value["image"]):
        raise ReleaseError("Image must include an immutable sha256 digest")
    if not 1 <= len(value["change_ref"]) <= 160 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/#-]*", value["change_ref"]):
        raise ReleaseError("Change reference must be a short ticket or PR identifier")
    return dict(value)


def atomic_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".candidate-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
            json.dump(obj, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def ensure_feature_branch(root: Path) -> str:
    proc = subprocess.run(["git", "-C", str(root), "branch", "--show-current"],
                          capture_output=True, text=True, check=False)
    branch = proc.stdout.strip()
    if proc.returncode or not branch or branch in {"main", "master"}:
        raise ReleaseError("Release preparation requires a checked-out feature branch, not main/master")
    # No shell execution, no remote operations, and no arbitrary commands from request files.
    return branch


def run_preflight(root: Path) -> list[str]:
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", "release_management/tests", "-p", "test_*.py"],
        ["git", "-C", str(root), "diff", "--check"],
    ]
    completed = []
    for cmd in commands:
        try:
            result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=90, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ReleaseError(f"Preflight could not complete: {cmd[0]}: {exc}") from exc
        if result.returncode:
            raise ReleaseError(f"Preflight failed ({' '.join(cmd)}): {(result.stderr + result.stdout)[-1500:]}")
        completed.append(" ".join(cmd))
    return completed


def prepare(root: Path, request: dict, *, write: bool = False, allow_production: bool = False,
            replace: bool = False, preflight: bool = True) -> dict:
    request = validate_request(request)
    branch = ensure_feature_branch(root)
    if request["environment"] == "production" and not allow_production:
        raise ReleaseError("Production preparation is blocked by default; require explicit --allow-production-preparation")
    path = root / "release_management" / "desired" / request["environment"] / (request["service"] + ".json")
    if path.exists() and read_json(path) != request and not replace:
        raise ReleaseError("Existing desired manifest differs; review it and pass --replace to change it")
    checks = run_preflight(root) if preflight else []
    report = {
        "mode": "PREPARE_ONLY_NO_DEPLOYMENT",
        "branch": branch,
        "requested": request,
        "candidate": str(path.relative_to(root)).replace("\\", "/"),
        "existing_candidate": path.exists(),
        "checks_run": checks,
        "effect": "source-controlled release-intent JSON only; no rollout, API call or approval granted",
    }
    if write:
        atomic_json(path, request)
        report["written"] = True
    else:
        report["written"] = False
    return report


def desired_inventory(root: Path) -> dict[tuple[str, str], dict]:
    root_path = root / "release_management" / "desired"
    results: dict[tuple[str, str], dict] = {}
    if not root_path.exists():
        return results
    for path in sorted(root_path.glob("*/*.json")):
        record = validate_request(read_json(path))
        if path.parent.name != record["environment"] or path.stem != record["service"]:
            raise ReleaseError(f"Manifest identity does not match file path: {path}")
        results[record["service"], record["environment"]] = record
    return results


class Ledger:
    """Local append-only evidence ledger; hash chain detects edits, not authenticated origin.

    Single writer only: exclusive lock file is created for writes and removed on exit.
    """

    def __init__(self, path: Path):
        self.path = path

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        events = []
        previous = "0" * 64
        try:
            with self.path.open("r", encoding="utf-8") as source:
                for line_no, line in enumerate(source, 1):
                    if not line.endswith("\n"):
                        raise ReleaseError(f"Ledger contains incomplete line {line_no}")
                    entry = json.loads(line)
                    if not isinstance(entry, dict) or set(entry) != {"record", "previous_hash", "hash"}:
                        raise ReleaseError(f"Malformed ledger entry at line {line_no}")
                    if entry["previous_hash"] != previous or entry["hash"] != digest({"record": entry["record"], "previous_hash": previous}):
                        raise ReleaseError(f"Ledger integrity failure at line {line_no}")
                    events.append(entry["record"])
                    previous = entry["hash"]
        except (OSError, ValueError, TypeError) as exc:
            if isinstance(exc, ReleaseError):
                raise
            raise ReleaseError(f"Cannot read ledger: {exc}") from exc
        return events

    def append_observation(self, request: dict, *, outcome: str, evidence: str, operator: str) -> dict:
        value = validate_request(request)
        if outcome not in {"succeeded", "failed"}:
            raise ReleaseError("Outcome must be succeeded or failed")
        if not re.fullmatch(r"https://[^\s]{10,500}", evidence):
            raise ReleaseError("Evidence must be an HTTPS URL pointing to the external deployment evidence")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@-]{1,100}", operator):
            raise ReleaseError("Operator must be a nonempty identifier")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ReleaseError(f"Ledger write is locked: {lock}; investigate before removing the lock") from exc
        try:
            os.close(fd)
            events = self.read()  # verify chain under lock before appending
            previous = "0" * 64
            if self.path.exists():
                with self.path.open("rb") as f:
                    lines = f.readlines()
                if lines:
                    previous = json.loads(lines[-1])["hash"]
            record = {
                "type": "operator_observation", "timestamp_utc": utc_now(),
                "operator_assertion": operator, "outcome": outcome,
                "evidence_url_unverified": evidence, "release": value,
            }
            entry = {"record": record, "previous_hash": previous}
            entry["hash"] = digest(entry)
            with self.path.open("a", encoding="utf-8", newline="\n") as sink:
                sink.write(canonical(entry).decode("utf-8") + "\n")
                sink.flush()
                os.fsync(sink.fileno())
            return record
        finally:
            lock.unlink(missing_ok=True)


def inventory(root: Path, ledger: Ledger) -> list[dict]:
    desired = desired_inventory(root)
    observed = {}
    for event in ledger.read():
        if event.get("type") != "operator_observation":
            raise ReleaseError("Unexpected ledger event type")
        rel = validate_request(event["release"])
        observed[(rel["service"], rel["environment"])] = event
    results = []
    for key in sorted(desired.keys() | observed.keys()):
        intention = desired.get(key)
        last = observed.get(key)
        actual = last["release"] if last and last["outcome"] == "succeeded" else None
        if last is None:
            state = "UNVERIFIED_NO_OBSERVATION"
        elif last["outcome"] == "failed":
            state = "FAILED_LAST_OBSERVATION"
        elif intention is None:
            state = "OBSERVED_WITHOUT_DECLARED_INTENT"
        elif (intention["image"], intention["commit"]) != (actual["image"], actual["commit"]):
            state = "DRIFT_REPORTED"
        else:
            state = "MATCHES_OPERATOR_ASSERTION_NOT_LIVE_VERIFIED"
        results.append({"service": key[0], "environment": key[1], "state": state,
                        "desired": intention, "last_successful_observation": actual,
                        "evidence": (last or {}).get("evidence_url_unverified"),
                        "observation_time": (last or {}).get("timestamp_utc")})
    return results
