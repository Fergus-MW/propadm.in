variable "project_id" {
  type = string
}
variable "region" {
  type = string
}
variable "images" {
  type = map(string)
}
variable "environment" {
  type = map(map(string))
}
variable "service_accounts" {
  type = map(string)
}
variable "secret_access" {
  type = map(list(string))
}
variable "secret_versions" {
  type = map(string)
}
variable "domain_services" {
  type = map(string)
}
variable "push_account" {
  type = string
}
variable "subnetwork" {
  description = "Direct VPC egress subnetwork; private ranges (SurrealDB) only."
  type        = string
}
resource "google_cloud_run_v2_service" "services" {
  for_each            = var.service_accounts
  project             = var.project_id
  name                = each.key
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  template {
    service_account = each.value
    timeout         = "3600s"
    # Graph services deserialize shared state and hold transactional copies in memory.
    max_instance_request_concurrency = each.key == "admin-panel" ? 80 : 2
    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        subnetwork = var.subnetwork
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = each.key == "browser" ? 1 : 10 # browser sessions live in process memory
    }
    containers {
      image = var.images[each.key]
      ports {
        container_port = each.key == "admin-panel" ? 3000 : 8080
      }
      resources {
        limits = { cpu = contains(["api", "agent"], each.key) ? "2" : "1", memory = each.key == "admin-panel" ? "512Mi" : (contains(["api", "agent"], each.key) ? "4Gi" : "2Gi")
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      dynamic "env" {
        for_each = lookup(var.environment, each.key, {})
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = { for id in lookup(var.secret_access, each.key, []) : id => var.secret_versions[id] if contains(keys(var.secret_versions), id)
        }
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
      startup_probe {
        initial_delay_seconds = 0
        period_seconds        = 10
        failure_threshold     = 12
        http_get {
          path = each.key == "admin-panel" ? "/" : "/healthz"
        }
      }
    }
  }
}
# Every service authenticates in the app (admin token, internal token or Google OIDC,
# provider webhook signatures), so Cloud Run IAM stays open; webhooks need it anyway.
resource "google_cloud_run_v2_service_iam_member" "public" {
  for_each = var.service_accounts
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.services[each.key].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
resource "google_cloud_run_domain_mapping" "domains" {
  for_each = var.domain_services
  project  = var.project_id
  location = var.region
  name     = each.key
  metadata {
    namespace = var.project_id
  }
  spec {
    route_name = google_cloud_run_v2_service.services[each.value].name
  }
}
output "urls" {
  value = { for k, v in google_cloud_run_v2_service.services : k => v.uri }
}
output "domain_records" {
  value = { for k, v in google_cloud_run_domain_mapping.domains : k => v.status[0].resource_records }
}
