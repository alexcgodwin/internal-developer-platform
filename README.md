# Internal Developer Platform

A portfolio-grade platform engineering project that shows how product teams can request environments, deploy services, and receive golden-path CI/CD, Kubernetes, observability, and policy controls.

## What this proves

- Platform engineering and developer self-service design
- Kubernetes namespace and workload onboarding
- GitOps-ready application delivery structure
- Terraform-managed platform foundation
- Cost-controlled validation with no always-on cloud resources

## Architecture

The platform is designed around four layers:

1. Foundation: networking, cluster access, registry, secrets and identity.
2. Developer workspace: namespace, quotas, service account, RBAC and policy.
3. Delivery: CI pipeline, image publish, GitOps sync and rollout health checks.
4. Operations: logs, metrics, SLOs, alerts and incident runbooks.

## Cost rule

This project is prepared locally first. Live resources are created only during a short validation window, then destroyed immediately.
