variable "project_id" {
  type = string
}
variable "access" {
  type = map(list(string))
}
variable "service_accounts" {
  type = map(string)
}
locals {
  ids = toset(flatten(values(var.access)))
  grants = { for pair in flatten([for svc, ids in var.access : [for id in ids : { svc = svc, id = id }]]) : "${pair.svc}/${pair.id}" => pair
  }
}
resource "google_secret_manager_secret" "secrets" {
  for_each  = local.ids
  project   = var.project_id
  secret_id = each.key
  replication {
    auto {}
  }
}
resource "google_secret_manager_secret_iam_member" "access" {
  for_each  = local.grants
  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.value.id].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_accounts[each.value.svc]}"
}
