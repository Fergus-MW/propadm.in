output "project_id" {
  value = local.project_id
}
output "state_bucket" {
  value = google_storage_bucket.state.name
}
output "name_servers" {
  value = try(google_dns_managed_zone.domain[0].name_servers, [])
}
output "dns_zone_name" {
  value = try(google_dns_managed_zone.domain[0].name, null)
}
output "build_service_account" {
  value = google_service_account.build.email
}
output "repository_id" {
  value = try(google_cloudbuildv2_repository.repository[0].id, null)
}
