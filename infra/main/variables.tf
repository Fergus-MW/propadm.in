variable "project_id" {
  type = string
}
variable "region" {
  type    = string
  default = "europe-west1"
}
variable "build_service_account" {
  type = string
}
variable "repository_id" {
  type    = string
  default = null
}
variable "domain" {
  type    = string
  default = "withproperly.com"
}
variable "dns_zone_name" {
  type    = string
  default = "propadmin"
}
variable "images" {
  description = "Full Artifact Registry digest or commit image for every service; no placeholder images."
  type        = map(string)
  validation {
    condition     = alltrue([for n in ["admin-panel", "api", "ingestion", "rules", "agent", "voice", "email", "browser"] : contains(keys(var.images), n)])
    error_message = "Supply an image for every service."
  }
}
variable "domain_services" {
  description = "Domain mappings require domain ownership verification. One hostname maps to one service."
  type        = map(string)
  default     = {}
}
variable "dns_records" {
  description = "Actual records returned by Cloud Run mappings and AgentMail; never invented DKIM/MX values. Keys are arbitrary stable IDs."
  type        = map(object({ name = string, type = string, ttl = optional(number, 300), rrdatas = list(string) }))
  default     = {}
}
variable "secret_versions" {
  description = "Only configured secrets are injected. Keys are secret IDs, values are version numbers. Populate Secret Manager outside Terraform."
  type        = map(string)
  default     = {}
}
variable "service_environment" {
  type    = map(map(string))
  default = {}
}
variable "posthog_project_token" {
  description = "Public PostHog ingestion token (phc_), never a personal API key. Empty disables analytics."
  type        = string
  default     = ""
  validation {
    condition     = var.posthog_project_token == "" || startswith(var.posthog_project_token, "phc_")
    error_message = "Use a public project token beginning phc_, not a personal API key."
  }
}
variable "signup_webhook_url" {
  description = "Chat webhook that receives each new landing signup. Empty disables it."
  type        = string
  default     = ""
  sensitive   = true
}
variable "posthog_host" {
  description = "PostHog ingestion host matching the project's region."
  type        = string
  default     = "https://us.i.posthog.com"
}
variable "enable_runtime" {
  description = "Explicit gate: runtime requires production shared durable repository and tested provider wiring. Local file storage is unsuitable for Cloud Run."
  type        = bool
  default     = false
}
variable "site_verification" {
  description = "Google Search Console TXT value (google-site-verification=...) proving domain ownership for Cloud Run domain mappings."
  type        = string
  default     = null
}
variable "enable_domain_mappings" {
  description = "Create Cloud Run domain mappings; requires the applying account to be a verified owner of the domain."
  type        = bool
  default     = false
}
variable "state_backend" {
  description = "Shared state store: gcs (legacy single JSON object) or surrealdb (switch after migrate_state.py)."
  type        = string
  default     = "gcs"
  validation {
    condition     = contains(["gcs", "surrealdb"], var.state_backend)
    error_message = "state_backend must be gcs or surrealdb."
  }
}
