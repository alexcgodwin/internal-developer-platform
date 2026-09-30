# Threat Model

| Threat | Control |
| --- | --- |
| Unreviewed production changes | Protected Git workflow and GitOps reconciliation |
| Privileged workloads | Non-root policy and restricted workload defaults |
| Lateral movement | Namespace boundaries and default-deny network policy |
| Resource exhaustion | Requests, limits and namespace quotas |
| Vulnerable configuration | CI validation and policy-as-code |
| Configuration drift | Git as deployment authority |
| Weak ownership | Required owner and cost-center metadata |
| Silent reliability degradation | SLOs, metrics and burn-rate alerts |

## Trust Boundaries
Developer workstation, source control, CI runner, artifact registry, GitOps controller and Kubernetes runtime are separate trust zones. Credentials should use short-lived workload identity where the target platform supports it.
