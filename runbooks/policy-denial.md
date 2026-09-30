# Runbook: Policy Denial

1. Read the admission-controller denial and identify the exact rule.
2. Confirm whether the workload violates the platform contract or needs an approved exception.
3. Fix the workload manifest before changing policy defaults.
4. If an exception is required, document owner, scope, expiry and compensating control.
5. Re-run validation and attach the result to the change record.
6. Remove expired exceptions during the weekly platform review.
