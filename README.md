# Internal Developer Platform

A platform engineering project that gives application teams a standard workspace, golden-path delivery structure, Kubernetes guardrails and operating evidence.

## What I Built

- Standard workspace and namespace onboarding pattern.
- Terraform-driven platform configuration and reusable outputs.
- Kubernetes quota, RBAC, health-check and deployment expectations.
- Validation scripts and evidence notes without permanent cluster spend.

## Delivery Workflow

1. Request a standard application workspace.
2. Apply namespace, quota, RBAC and policy conventions.
3. Deploy through the golden-path structure.
4. Validate configuration and record the result.
5. Hand over clear ownership and operating boundaries.

## Repository Structure

| Path | Purpose |
| --- | --- |
| `terraform/` | Workspace policy and reusable outputs. |
| `kubernetes/` | Golden-path namespace and application resources. |
| `docs/evidence/` | Validation and engineering proof notes. |
| `scripts/` | Repeatable validation commands. |

## Validation

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate.ps1
```

## Engineering Controls

| Control | Senior engineering concern |
| --- | --- |
| Onboarding | Standard workspace and namespace entry point. |
| Governance | Quota, RBAC, policy and ownership boundaries. |
| Delivery | Golden-path structure with explicit escape hatches. |
| Operations | Validation, evidence and reviewable change. |

## Failure and Review Model

The platform considers invalid workspace requests, quota conflicts, missing ownership, unhealthy workloads and policy exceptions before they become application-team incidents.

## Completed Result

A structured internal developer platform pattern for standard workspaces, guardrails and repeatable delivery, presented as an operating model rather than a collection of basic manifests.

## Engineering Value

This project demonstrates developer experience, governance, Kubernetes boundaries, delivery controls and reviewable platform evidence.