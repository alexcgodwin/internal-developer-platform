# Offline release preparation and inventory

This is a zero-paid-service **local demonstration** of three connected platform capabilities: reusable Claude Code skills, deterministic release preparation, and an operator-attested release inventory. It deliberately does **not** connect to or deploy into Kubernetes, AWS, Azure, GitHub or a container registry. There is no AI API or API key in the Python program.

## Try it

Use Python 3.10+ and Git. The repository uses `master` as its default branch; first create a feature branch. No extra pip dependencies:

```bash
git switch master
git pull --ff-only origin master
git switch -c feature/local-release-control-plane
python -m unittest discover -s release_management/tests -p 'test_*.py'
python -m release_management prepare --request release_management/examples/guestbook-dev.json
python -m release_management prepare --request release_management/examples/guestbook-dev.json --write
python -m release_management inventory
python -m release_management audit
```

The request in `examples/` contains a **fake** commit, digest and registry path. It is not an actual deployable artifact. Replace it with a real image digest and source commit when preparing a real promotion request. The first `prepare` command is a dry run; `--write` creates or updates only `release_management/desired/dev/guestbook-api.json`, a proposed release-intent file tracked in Git. This file is **not wired to Argo CD or any deployment controller**. Review the diff and open a PR. `prepare` refuses to write on `master` or `main`; production intent is blocked unless `--allow-production-preparation` is explicitly specified, and even then it never deploys. `--replace` is additionally required to change an existing desired candidate.

The agent runs a fixed allowlist of preflight checks: Python unit tests and `git diff --check`. It does not run arbitrary code supplied by a release request. This is a **deterministic release-preparation agent**, not an autonomous production release controller. Actual CI results, artifact provenance, security approvals and human review must be verified externally. Avoid using the example manifest in live release processes.

## Observation ledger and release inventory

An authorized operator may optionally record a *claim* about an independently verified deployment:

```bash
python -m release_management record-observation \
  --request path/to/real-release-request.json \
  --outcome succeeded \
  --evidence-url https://example.org/ci/deployments/1234 \
  --operator team-member-id
python -m release_management inventory
python -m release_management audit
```

The observation command stores records under `.local/release-tracking/observations.jsonl`, excluded from Git. It never queries the evidence URL and does not verify the caller's identity. A hash chain helps detect edits to existing entries, but cannot prove authenticity, detect deletion of the complete ledger or establish an independent anchor. The lock file prevents concurrent local writes; investigate a leftover `.lock` file rather than removing it blindly. Preserve external audited deployment logs as the actual evidence source.

The inventory merges the desired candidates in `release_management/desired/` with the most recent local observation per service/environment. Reported states distinguish: no observation, failed last observation, reported drift, and matching but **not independently verified** evidence. `inventory` never claims that a deployment actually happened. The local ledger is not shared between engineers. A real implementation should query GitHub deployment records plus Kubernetes/Argo CD observed state, enforce signed workload identity and retain audit data in an access-controlled shared store.

## Claude Code skills

The three documented skills live in `.claude/skills/`: `release-readiness`, `release-inventory`, `release-incident-evidence`. They call the deterministic local program. Skills can be committed and tested without Claude Code or paying for an AI model. **Do not claim other engineers use the skills until actual independent adoption is documented.**

## Validation and release gates

`.github/workflows/release-governance.yml` executes offline unit tests and validates that skill metadata and file paths exist. The workflow has `contents: read`, no deployment tokens, no cloud login and no secret requirements. It is enabled only on changes to the release-management module, its skill files, documentation or CI workflow. The repository's separate platform validation workflow remains unchanged.

PR review and appropriate branch protections remain necessary to merge. A successful unit test or candidate creation is **not** proof of release approval, real cluster state or recovery testing.

## Guardrails and limitations

- No paid external calls, deployment, cluster mutation, GitHub writes or production rollouts.
- No passwords, secret values, kubeconfigs, cloud credentials or SSH keys in release requests or tracked desired manifests.
- Immutable image digests and full commit IDs are required for candidate manifests. The tool validates their *format*, not their existence or authenticity.
- A feature branch is mandatory when preparing a release. No branch is merged automatically.
- Production candidate creation is opt-in and still only writes a JSON file for PR review.
- Multiple contributors need their own ledgers; current single-host lock is not a distributed lock. Implement shared evidence and identity verification before adopting production tracking.
- CI runners on public GitHub repositories typically have no GitHub Actions minute charge for standard runners; service plans and policies can change. No cloud infrastructure is provisioned by this feature.
