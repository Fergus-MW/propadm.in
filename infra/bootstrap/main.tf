provider "google" {
  project = var.project_id
  region  = var.region
}
# Set create_project = false to bootstrap into an existing project.
resource "google_project" "project" {
  count           = var.create_project ? 1 : 0
  project_id      = var.project_id
  name            = "Propadmin"
  billing_account = var.billing_account
  org_id          = var.org_id
  folder_id       = var.folder_id
}
locals {
  project_id = var.create_project ? google_project.project[0].project_id : var.project_id
  apis       = toset(["run.googleapis.com", "artifactregistry.googleapis.com", "cloudbuild.googleapis.com", "pubsub.googleapis.com", "secretmanager.googleapis.com", "storage.googleapis.com", "dns.googleapis.com", "aiplatform.googleapis.com", "iam.googleapis.com", "serviceusage.googleapis.com", "cloudscheduler.googleapis.com"])
}
resource "google_project_service" "apis" {
  for_each           = local.apis
  project            = local.project_id
  service            = each.value
  disable_on_destroy = false
}
resource "google_storage_bucket" "state" {
  project                     = local.project_id
  name                        = "${var.project_id}-tf-state"
  location                    = "EU"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning {
    enabled = true
  }
  depends_on = [google_project_service.apis]
}
resource "google_dns_managed_zone" "domain" {
  count       = var.create_dns_zone ? 1 : 0
  project     = local.project_id
  name        = "propadmin"
  dns_name    = "${var.domain}."
  description = "Propadmin DNS; set these nameservers at the registrar"
  depends_on  = [google_project_service.apis]
}
resource "google_service_account" "build" {
  project      = local.project_id
  account_id   = "propadmin-build"
  display_name = "Propadmin Cloud Build deployer"
  depends_on   = [google_project_service.apis]
}
resource "google_project_iam_member" "build_roles" {
  for_each = toset(["roles/logging.logWriter", "roles/run.admin", "roles/artifactregistry.writer", "roles/serviceusage.serviceUsageConsumer", "roles/viewer"])
  project  = local.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.build.email}"
}
resource "google_storage_bucket_iam_member" "build_state" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.build.email}"
}
resource "google_cloudbuildv2_connection" "github" {
  count    = var.github_repository_url == null ? 0 : 1
  project  = local.project_id
  location = var.region
  name     = "propadmin-github"
  github_config {
    app_installation_id = var.github_app_installation_id
    authorizer_credential {
      oauth_token_secret_version = var.github_token_secret_version
    }
  }
  depends_on = [google_project_service.apis]
}
resource "google_cloudbuildv2_repository" "repository" {
  count             = var.github_repository_url == null ? 0 : 1
  project           = local.project_id
  location          = var.region
  name              = "propadmin"
  parent_connection = google_cloudbuildv2_connection.github[0].id
  remote_uri        = var.github_repository_url
}
