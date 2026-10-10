variable "landing_image" {
  type        = string
  default     = null
  description = "Container image for the public landing page; null disables it."
}

resource "google_service_account" "landing" {
  count        = var.landing_image == null ? 0 : 1
  account_id   = "propadmin-landing"
  display_name = "Properly landing signup storage"
}

resource "google_storage_bucket" "signups" {
  count                       = var.landing_image == null ? 0 : 1
  name                        = "${var.project_id}-signups"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_storage_bucket_iam_member" "landing_signups" {
  count  = var.landing_image == null ? 0 : 1
  bucket = google_storage_bucket.signups[0].name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.landing[0].email}"
}

resource "google_cloud_run_v2_service" "landing" {
  count               = var.landing_image == null ? 0 : 1
  name                = "landing"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  template {
    service_account                  = google_service_account.landing[0].email
    max_instance_request_concurrency = 40
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    containers {
      image = var.landing_image
      ports {
        container_port = 8080
      }
      resources {
        limits            = { cpu = "1", memory = "256Mi" }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      env {
        name  = "SIGNUPS_BUCKET"
        value = google_storage_bucket.signups[0].name
      }
      startup_probe {
        http_get {
          path = "/healthz"
        }
      }
    }
  }
  depends_on = [google_storage_bucket_iam_member.landing_signups]
}

resource "google_cloud_run_v2_service_iam_member" "landing_public" {
  count    = var.landing_image == null ? 0 : 1
  location = var.region
  name     = google_cloud_run_v2_service.landing[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "landing_url" {
  value = try(google_cloud_run_v2_service.landing[0].uri, null)
}
