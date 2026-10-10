variable "project_id" {
  type = string
}
variable "project_number" {
  type = string
}
variable "service_urls" {
  type = map(string)
}
variable "service_accounts" {
  type = map(string)
}
variable "push_account" {
  type = string
}
locals {
  stages       = { land = "ingestion", parse = "ingestion", chunk = "ingestion", extract = "ingestion", resolve = "ingestion", embed = "ingestion", link = "ingestion" }
  publishers   = { api = ["land"], ingestion = ["parse", "chunk", "extract", "resolve", "embed", "link"] }
  grants       = { for pair in flatten([for svc, topics in local.publishers : [for topic in topics : { svc = svc, topic = topic }]]) : "${pair.svc}/${pair.topic}" => pair }
  pubsub_agent = "service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
resource "google_pubsub_topic" "stage" {
  for_each                   = local.stages
  project                    = var.project_id
  name                       = "propadmin-${each.key}"
  message_retention_duration = "604800s"
}
resource "google_pubsub_topic" "dead" {
  for_each = local.stages
  project  = var.project_id
  name     = "propadmin-${each.key}-dead"
}
resource "google_pubsub_subscription" "dead" {
  for_each                   = local.stages
  project                    = var.project_id
  name                       = "propadmin-${each.key}-dead-inspect"
  topic                      = google_pubsub_topic.dead[each.key].id
  message_retention_duration = "604800s"
  expiration_policy {
    ttl = ""
  }
}
resource "google_pubsub_subscription" "push" {
  for_each = { for stage, svc in local.stages : stage => svc if contains(keys(var.service_urls), svc)
  }
  project              = var.project_id
  name                 = "propadmin-${each.key}"
  topic                = google_pubsub_topic.stage[each.key].id
  ack_deadline_seconds = 600
  expiration_policy {
    ttl = ""
  }
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead[each.key].id
    max_delivery_attempts = 5
  }
  push_config {
    push_endpoint = "${var.service_urls[each.value]}/internal/events/${each.key}"
    oidc_token {
      service_account_email = var.push_account
      audience              = var.service_urls[each.value]
    }
  }
  depends_on = [google_pubsub_topic_iam_member.dead_publisher]
}
resource "google_pubsub_topic_iam_member" "publishers" {
  for_each = local.grants
  project  = var.project_id
  topic    = google_pubsub_topic.stage[each.value.topic].name
  role     = "roles/pubsub.publisher"
  member   = "serviceAccount:${var.service_accounts[each.value.svc]}"
}
resource "google_pubsub_topic_iam_member" "dead_publisher" {
  for_each = local.stages
  project  = var.project_id
  topic    = google_pubsub_topic.dead[each.key].name
  role     = "roles/pubsub.publisher"
  member   = "serviceAccount:${local.pubsub_agent}"
}
resource "google_pubsub_subscription_iam_member" "dead_ack" {
  for_each     = google_pubsub_subscription.push
  project      = var.project_id
  subscription = each.value.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${local.pubsub_agent}"
}
resource "google_service_account_iam_member" "oidc" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.push_account}"
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${local.pubsub_agent}"
}
output "topics" {
  value = { for k, v in google_pubsub_topic.stage : k => v.id }
}
