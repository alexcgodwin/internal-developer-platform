# Runbook: Deployment Failure

## Trigger
GitOps sync fails, rollout stalls, or readiness does not converge.

## Response
1. Confirm the failing environment and last known-good commit.
2. Inspect GitOps sync status and Kubernetes rollout events.
3. Check image availability, configuration, secrets and policy denials.
4. Compare rendered Helm output with the last successful release.
5. Roll back by reverting the Git commit when user impact is material.
6. Validate health, SLO signals and error budget after recovery.

## Evidence
Capture commit SHA, failed resource, policy result, timestamps and recovery action.
