# ADR 0001: GitOps as Deployment Authority

## Status
Accepted

## Context
Direct cluster changes create drift, weak auditability and inconsistent promotion.

## Decision
Git is the deployment source of truth. CI validates changes; GitOps reconciles approved desired state. Emergency cluster changes must be followed by a repository change or revert.

## Consequences
- Promotion becomes reviewable and reproducible.
- Rollback is a Git operation with an auditable history.
- Drift is visible instead of becoming an undocumented operating state.
- Platform availability depends on healthy reconciliation and repository controls.
