# Workspace Onboarding Runbook

## Goal

Create a standard application workspace that gives a team a predictable Kubernetes boundary, a deployment path and operating evidence.

## Steps

1. Confirm the owning team, service name and environment.
2. Apply the namespace and label standard.
3. Apply resource quota and deployment manifest.
4. Run validation checks.
5. Capture evidence under `docs/evidence/`.
6. Review production additions such as policy controller, GitOps promotion and monitoring alerts.

## Production Notes

A production platform would connect this pattern to an intake portal, a GitOps controller, admission policies, SSO-backed RBAC and service catalog ownership metadata.