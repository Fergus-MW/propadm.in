variable "project_id" {
  type = string
}
variable "region" {
  type = string
}
resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "propadmin"
  description   = "Propadmin container images"
  format        = "DOCKER"
}
output "repository" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}
