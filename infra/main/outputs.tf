output "service_urls" {
  value = var.enable_runtime ? module.cloud_run[0].urls : {}
}
output "image_repository" {
  value = module.artifact_registry.repository
}
output "buckets" {
  value = module.storage.buckets
}
output "domain_records" {
  value = var.enable_runtime ? module.cloud_run[0].domain_records : {}
}
output "topics" {
  value = module.pubsub.topics
}
output "runtime_enabled" {
  value = var.enable_runtime
}
