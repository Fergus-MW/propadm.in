variable "project_id" {
  type = string
}
variable "region" {
  type = string
}
variable "repository_id" {
  type = string
}
variable "build_service_account" {
  type = string
}
locals {
  names = toset(["admin-panel", "api", "ingestion"])
}
resource "google_cloudbuild_trigger" "pr" {
  project         = var.project_id
  location        = var.region
  name            = "propadmin-pr-checks"
  service_account = "projects/${var.project_id}/serviceAccounts/${var.build_service_account}"
  filename        = "cloudbuild/pr-checks.yaml"
  repository_event_config {
    repository = var.repository_id
    pull_request {
      branch = "^main$"
    }
  }
}
resource "google_cloudbuild_trigger" "services" {
  for_each        = local.names
  project         = var.project_id
  location        = var.region
  name            = "propadmin-deploy-${each.key}"
  service_account = "projects/${var.project_id}/serviceAccounts/${var.build_service_account}"
  filename        = each.key == "admin-panel" ? "cloudbuild/admin-panel.yaml" : "services/${each.key}/cloudbuild.yaml"
  included_files  = each.key == "admin-panel" ? ["services/admin-panel/**", "pnpm-lock.yaml", "package.json"] : ["services/${each.key}/**", "packages/core/**", "packages/runtime/**", "pyproject.toml", "uv.lock"]
  substitutions = { _REGION = var.region, _SERVICE = each.key
  }
  repository_event_config {
    repository = var.repository_id
    push {
      branch = "^main$"
    }
  }
}
