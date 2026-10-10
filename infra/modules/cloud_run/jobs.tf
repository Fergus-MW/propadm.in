variable "raw_bucket" {
  type = string
}
locals {
  jobs = {
    migrations = { service = "ingestion", command = ["python", "-m", "db.schema.apply"]
    }
    backfill = { service = "ingestion", command = ["python", "/app/infra/scripts/run_job.py", "backfill"]
    }
    rules-recompute = { service = "rules", command = ["python", "-m", "app.job"]
    }

  }
}
resource "google_cloud_run_v2_job" "jobs" {
  for_each            = local.jobs
  project             = var.project_id
  location            = var.region
  name                = "propadmin-${each.key}"
  deletion_protection = false
  template {
    template {
      service_account = each.key == "backfill" ? var.push_account : var.service_accounts[each.value.service]
      timeout         = "3600s"
      max_retries     = 1
      containers {
        image   = var.images[each.value.service]
        command = each.value.command
        env {
          name  = "TARGET_SERVICE_URL"
          value = google_cloud_run_v2_service.services[each.value.service].uri
        }
        env {
          name  = "RAW_BUCKET"
          value = var.raw_bucket
        }
        # Jobs run with their service's full configuration and secrets.
        dynamic "env" {
          for_each = each.key == "backfill" ? {} : lookup(var.environment, each.value.service, {})
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = { for id in lookup(var.secret_access, each.value.service, []) : id => var.secret_versions[id] if contains(keys(var.secret_versions), id) && each.key != "backfill" }
          content {
            name = upper(replace(env.key, "-", "_"))
            value_source {
              secret_key_ref {
                secret  = env.key
                version = env.value
              }
            }
          }
        }
      }
    }
  }
}
