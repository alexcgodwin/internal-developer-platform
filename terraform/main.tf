terraform {
  required_version = ">= 1.6.0"
}

variable "platform_name" {
  type    = string
  default = "internal-developer-platform"
}

locals {
  namespaces = {
    dev  = { cpu = "2", memory = "4Gi" }
    test = { cpu = "2", memory = "4Gi" }
    prod = { cpu = "4", memory = "8Gi" }
  }
}

output "platform_name" {
  value = var.platform_name
}

output "workspace_policy" {
  value = local.namespaces
}
