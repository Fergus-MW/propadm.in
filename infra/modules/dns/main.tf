variable "zone_name" {
  type = string
}
variable "records" {
  type = map(object({ name = string, type = string, ttl = number, rrdatas = list(string) }))
}
resource "google_dns_record_set" "records" {
  for_each     = var.records
  managed_zone = var.zone_name
  name         = each.value.name
  type         = each.value.type
  ttl          = each.value.ttl
  rrdatas      = each.value.rrdatas
}
