---
name: release-inventory
description: Show planned and operator-reported application versions by environment, and identify missing evidence or potential version drift. Use for release audit and deployment inventory questions.
---

# Release inventory

1. From the repository root run `python -m release_management inventory`.
2. Distinguish source-controlled **desired intents** from **operator-asserted observed deployments**. The tool does not query a live Kubernetes cluster, GitHub deployments, or a container registry.
3. Report `UNVERIFIED_NO_OBSERVATION`, `FAILED_LAST_OBSERVATION`, and `DRIFT_REPORTED` as risks requiring human investigation.
4. Treat `MATCHES_OPERATOR_ASSERTION_NOT_LIVE_VERIFIED` as an assertion rather than verified runtime health.
5. To inspect ledger integrity run `python -m release_management audit`. A passing hash-chain audit does not authenticate operators or prove all observations were recorded.
6. Do not claim a rollout, production adoption, or a live environment based solely on the generated files. Require verified deployment evidence and an authorized approval trail.
