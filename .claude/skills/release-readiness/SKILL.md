---
name: release-readiness
description: Validate an immutable release request and prepare a reviewable GitOps release-intent candidate without making deployments. Use when an engineer requests a release readiness check.
---

# Release readiness

Use the repository's offline Python tool. Do not infer successful cloud deployment, CI status, container signing, or approval from the request. Never use a cloud CLI or credentials for this skill.

1. Identify the service, intended environment, semver version, exact 40-character source commit, immutable `sha256` image digest and change/PR reference. If any item is missing, stop rather than guess.
2. Confirm the engineer is on a feature branch, with work safely saved.
3. Run `python -m release_management prepare --request path/to/request.json` from the repository root. It runs repository unit tests and `git diff --check` before showing a preview.
4. Explain that the preview only prepares an intent change. It does not validate the remote registry or CI, deploy anything, or authorize production.
5. Only with the engineer's explicit approval to modify files, run `python -m release_management prepare --request path/to/request.json --write`. If the target exists and differs, examine the diff; request approval before passing `--replace`.
6. Present the Git diff and advise a pull request with real CI checks and human review. Never merge or run a production deployment.

The sample request in `release_management/examples/guestbook-dev.json` contains **fake commit and image identifiers**, for testing only.
