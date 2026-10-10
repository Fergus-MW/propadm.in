provider "google" {
  project = var.project_id
  region  = var.region
}
data "google_project" "current" {
  project_id = var.project_id
}
locals {
  python = ["api", "ingestion", "rules", "agent", "voice", "email", "browser"]
  names  = toset(concat(["admin-panel"], local.python))
  core   = ["admin-password", "internal-service-token", "token-secret"]
  analytics = {
    POSTHOG_PROJECT_TOKEN = var.posthog_project_token
    POSTHOG_HOST          = var.posthog_host
  }
  provider = {
    api       = ["anthropic-api-key"]
    ingestion = ["anthropic-api-key"]
    rules     = ["anthropic-api-key"]
    agent     = ["anthropic-api-key"]
    voice     = ["anthropic-api-key", "elevenlabs-api-key", "elevenlabs-webhook-secret", "elevenlabs-tool-secret"]
    email     = ["anthropic-api-key", "agentmail-api-key", "agentmail-webhook-secret"]
    browser   = ["anthropic-api-key", "browserbase-api-key"]
  }
  secret_access = merge(
    { for name in local.python : name => concat(local.core, local.provider[name]) },
    { admin-panel = [] },
  )
  # Cloud Run v2 URLs are deterministic, so services can reference each other without cycles.
  urls = { for name in local.names : name => "https://${name}-${data.google_project.current.number}.${var.region}.run.app" }
  environment = merge(
    { for name in local.python : name => merge(
      {
        PROPADMIN_MODE                  = "cloud"
        PROPADMIN_DATA_PATH             = "gs://${module.storage.buckets["state"]}/state.json"
        GOOGLE_CLOUD_PROJECT            = var.project_id
        OBSERVABILITY_ARTIFACT_BUCKET   = module.storage.buckets["artifacts"]
        SERVICE_BASE_URL                = local.urls[name]
        INTERNAL_CALLER_SERVICE_ACCOUNT = google_service_account.push.email
        PUBLIC_API_URL                  = local.urls["api"]
        MCP_SERVER_URL                  = "${local.urls["api"]}/mcp"
        RULES_SERVICE_URL               = local.urls["rules"]
        AGENT_SERVICE_URL               = local.urls["agent"]
        VOICE_SERVICE_URL               = local.urls["voice"]
        EMAIL_SERVICE_URL               = local.urls["email"]
        BROWSER_SERVICE_URL             = local.urls["browser"]
        INGESTION_SERVICE_URL           = local.urls["ingestion"]
      },
      local.analytics,
      # These services ingest documents, email bodies/attachments and call transcripts.
      # Local development retains the credential-free extractor.
      contains(["api", "ingestion", "email", "voice"], name) ? {
        EXTRACTION_PROVIDER = "claude"
        PIPELINE_MODEL      = "claude-haiku-5-5"
      } : {},
      lookup(var.service_environment, name, {}),
    ) },
    { admin-panel = merge({ API_URL = local.urls["api"] }, local.analytics, lookup(var.service_environment, "admin-panel", {})) },
  )
}
resource "google_service_account" "services" {
  for_each     = local.names
  account_id   = "propadmin-${each.key}"
  display_name = "Propadmin ${each.key}"
}
resource "google_service_account" "push" {
  account_id   = "propadmin-events"
  display_name = "Authenticated PubSub and backfill delivery"
}
resource "google_service_account_iam_member" "build_act_as" {
  for_each           = google_service_account.services
  service_account_id = each.value.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.build_service_account}"
}
resource "google_service_account_iam_member" "build_push_act_as" {
  service_account_id = google_service_account.push.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.build_service_account}"
}
module "artifact_registry" {
  source     = "../modules/artifact_registry"
  project_id = var.project_id
  region     = var.region
}
module "storage" {
  source     = "../modules/storage"
  project_id = var.project_id
  service_accounts = { for k, v in google_service_account.services : k => v.email
  }
}
module "secrets" {
  source     = "../modules/secrets"
  project_id = var.project_id
  access     = local.secret_access
  service_accounts = { for k, v in google_service_account.services : k => v.email
  }
}
module "cloud_run" {
  count       = var.enable_runtime ? 1 : 0
  source      = "../modules/cloud_run"
  project_id  = var.project_id
  region      = var.region
  images      = var.images
  environment = local.environment
  service_accounts = { for k, v in google_service_account.services : k => v.email
  }
  secret_access   = local.secret_access
  secret_versions = var.secret_versions
  domain_services = var.enable_domain_mappings ? var.domain_services : {}
  push_account    = google_service_account.push.email
  raw_bucket      = module.storage.buckets["raw"]
  depends_on      = [module.secrets]
}
module "pubsub" {
  source         = "../modules/pubsub"
  project_id     = var.project_id
  project_number = data.google_project.current.number
  service_urls   = var.enable_runtime ? module.cloud_run[0].urls : {}
  service_accounts = { for k, v in google_service_account.services : k => v.email
  }
  push_account = google_service_account.push.email
}
module "dns" {
  source    = "../modules/dns"
  zone_name = var.dns_zone_name
  # Subdomain mappings always CNAME to ghs.googlehosted.com; verification TXT sits at the apex.
  records = merge(
    var.dns_records,
    { for host, _ in var.domain_services : "map-${host}" => {
      name = "${host}.", type = "CNAME", ttl = 300, rrdatas = ["ghs.googlehosted.com."]
    } },
    var.site_verification == null ? {} : { site-verification = {
      name = "${var.domain}.", type = "TXT", ttl = 300, rrdatas = ["\"${var.site_verification}\""]
    } },
  )
}
module "cloud_build" {
  count                 = var.repository_id == null ? 0 : 1
  source                = "../modules/cloud_build"
  project_id            = var.project_id
  region                = var.region
  repository_id         = var.repository_id
  build_service_account = var.build_service_account
}

resource "google_storage_bucket_iam_member" "job_raw_reader" {
  bucket = module.storage.buckets["raw"]
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.push.email}"
}

resource "google_project_iam_member" "embedding_access" {
  for_each = toset(["api", "ingestion"])
  project  = var.project_id
  role     = "roles/aiplatform.user"
  member   = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Shared durable state (GcsStore); every Python service reads and CAS-writes one object.
resource "google_storage_bucket_iam_member" "state" {
  for_each = toset(local.python)
  bucket   = module.storage.buckets["state"]
  role     = "roles/storage.objectUser"
  member   = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Evidence blobs are create-only. Runtime services cannot overwrite or delete prior evidence.
resource "google_storage_bucket_iam_member" "evidence_writer" {
  for_each = toset(local.python)
  bucket   = module.storage.buckets["artifacts"]
  role     = "roles/storage.objectCreator"
  member   = "serviceAccount:${google_service_account.services[each.key].email}"
  condition {
    title      = "execution-evidence-only"
    expression = "resource.name.startsWith(\"projects/_/buckets/${module.storage.buckets["artifacts"]}/objects/evidence/\")"
  }
}

# Browser credentials: the API writes propadmin-credential-* secrets, the browser reads them.
locals {
  credential_condition = "resource.name.startsWith(\"projects/${data.google_project.current.number}/secrets/propadmin-credential-\")"
}
resource "google_project_iam_member" "credential_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.services["api"].email}"
  condition {
    title      = "propadmin-credentials-only"
    expression = local.credential_condition
  }
}
resource "google_project_iam_member" "credential_reader" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.services["browser"].email}"
  condition {
    title      = "propadmin-credentials-only"
    expression = local.credential_condition
  }
}

# Cloud Scheduler stands in for Cloud Tasks: a minute sweep wakes due agent runs,
# and a nightly full edge recompute refreshes rules and layout.
locals {
  schedules = {
    agent-wakeups = { service = "agent", path = "/internal/wakeups/due", schedule = "* * * * *" }
    rules-nightly = { service = "rules", path = "/internal/recompute", schedule = "0 3 * * *" }
    rent-daily    = { service = "rules", path = "/internal/rent-schedule", schedule = "5 0 * * *" }
  }
}
resource "google_cloud_scheduler_job" "schedules" {
  for_each         = var.enable_runtime ? local.schedules : {}
  project          = var.project_id
  region           = var.region
  name             = "propadmin-${each.key}"
  schedule         = each.value.schedule
  time_zone        = "Europe/London"
  attempt_deadline = "600s"
  http_target {
    http_method = "POST"
    uri         = "${local.urls[each.value.service]}${each.value.path}"
    headers     = { "Content-Type" = "application/json" }
    body        = base64encode("{}")
    oidc_token {
      service_account_email = google_service_account.push.email
      audience              = local.urls[each.value.service]
    }
  }
  depends_on = [module.cloud_run]
}
