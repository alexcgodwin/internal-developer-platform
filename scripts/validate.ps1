$ErrorActionPreference = 'Stop'

Write-Host '== Internal Developer Platform local validation =='
terraform -chdir=terraform init -backend=false -input=false
terraform -chdir=terraform validate

$manifest = Get-Content kubernetes/golden-path-app.yaml -Raw
foreach ($required in @('apiVersion:', 'kind:', 'metadata:', 'Deployment', 'Service')) {
  if ($manifest -notmatch [regex]::Escape($required)) {
    throw "Kubernetes manifest missing required marker: $required"
  }
}

Write-Host 'Validation complete. No cloud resources were created.'
