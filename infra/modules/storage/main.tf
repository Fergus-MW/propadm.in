variable "project_id" {
  type = string
}
variable "service_accounts" {
  type = map(string)
}
resource "google_storage_bucket" "buckets" {
  for_each                    = toset(["raw", "artifacts", "state"])
  name                        = "${var.project_id}-${each.key}"
  project                     = var.project_id
  location                    = "EU"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning {
    enabled = true
  }
  # The state object is rewritten on every mutation; keep a short version trail.
  lifecycle_rule {
    condition {
      num_newer_versions = 20
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }
}
locals {
  writers = { ingestion = "raw" }
}
resource "google_storage_bucket_iam_member" "writers" {
  for_each = local.writers
  bucket   = google_storage_bucket.buckets[each.value].name
  role     = "roles/storage.objectUser"
  member   = "serviceAccount:${var.service_accounts[each.key]}"
}
resource "google_storage_bucket_iam_member" "api_reader" {
  for_each = google_storage_bucket.buckets
  bucket   = each.value.name
  role     = "roles/storage.objectViewer"
  member   = "serviceAccount:${var.service_accounts["api"]}"
}
output "buckets" {
  value = { for k, v in google_storage_bucket.buckets : k => v.name }
}
