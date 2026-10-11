# Shared state in SurrealDB on one private VM; Cloud Run reaches it over Direct VPC egress.
# ponytail: single VM with daily disk snapshots (RPO 24h, manual failover); a replica or
# SurrealDB Cloud is the upgrade path if that recovery window stops being acceptable.
locals {
  surreal_ip = "10.20.0.10"
}
resource "google_compute_network" "private" {
  name                    = "propadmin"
  auto_create_subnetworks = false
}
resource "google_compute_subnetwork" "private" {
  name                     = "propadmin-${var.region}"
  region                   = var.region
  network                  = google_compute_network.private.id
  ip_cidr_range            = "10.20.0.0/24"
  private_ip_google_access = true
}
# Outbound only, so the VM can pull its image without a public IP.
resource "google_compute_router" "nat" {
  name    = "propadmin-nat"
  region  = var.region
  network = google_compute_network.private.id
}
resource "google_compute_router_nat" "nat" {
  name                               = "propadmin-nat"
  router                             = google_compute_router.nat.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}
resource "google_compute_firewall" "surreal" {
  name          = "propadmin-surreal-from-cloud-run"
  network       = google_compute_network.private.id
  source_ranges = [google_compute_subnetwork.private.ip_cidr_range]
  target_tags   = ["surrealdb"]
  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }
}
resource "google_compute_firewall" "iap_ssh" {
  name          = "propadmin-iap-ssh"
  network       = google_compute_network.private.id
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["surrealdb"]
  allow {
    protocol = "tcp"
    ports    = ["22", "8000"] # 8000: operator tunnels for migrate_state.py
  }
}
resource "google_compute_address" "surreal" {
  name         = "propadmin-surreal"
  region       = var.region
  subnetwork   = google_compute_subnetwork.private.id
  address_type = "INTERNAL"
  address      = local.surreal_ip
}
resource "google_service_account" "surreal" {
  account_id   = "propadmin-surrealdb"
  display_name = "Propadmin SurrealDB VM"
}
resource "google_secret_manager_secret_iam_member" "surreal_vm" {
  secret_id  = "surreal-password"
  role       = "roles/secretmanager.secretAccessor"
  member     = "serviceAccount:${google_service_account.surreal.email}"
  depends_on = [module.secrets]
}
resource "google_project_iam_member" "surreal_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.surreal.email}"
}
resource "google_compute_resource_policy" "surreal_snapshots" {
  name   = "propadmin-surreal-daily"
  region = var.region
  snapshot_schedule_policy {
    schedule {
      daily_schedule {
        days_in_cycle = 1
        start_time    = "03:00"
      }
    }
    retention_policy {
      max_retention_days    = 14
      on_source_disk_delete = "KEEP_AUTO_SNAPSHOTS"
    }
  }
}
resource "google_compute_disk" "surreal" {
  name = "propadmin-surreal-data"
  zone = "${var.region}-b"
  type = "pd-ssd"
  size = 50
  lifecycle {
    prevent_destroy = true
  }
}
resource "google_compute_disk_resource_policy_attachment" "surreal" {
  name = google_compute_resource_policy.surreal_snapshots.name
  disk = google_compute_disk.surreal.name
  zone = google_compute_disk.surreal.zone
}
resource "google_compute_instance" "surreal" {
  name                      = "propadmin-surrealdb"
  zone                      = google_compute_disk.surreal.zone
  machine_type              = "e2-standard-2"
  tags                      = ["surrealdb"]
  allow_stopping_for_update = true
  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
      size  = 20
    }
  }
  attached_disk {
    source      = google_compute_disk.surreal.id
    device_name = "surreal-data"
  }
  network_interface {
    subnetwork = google_compute_subnetwork.private.id
    network_ip = google_compute_address.surreal.address
  }
  shielded_instance_config {
    enable_secure_boot = true
  }
  service_account {
    email  = google_service_account.surreal.email
    scopes = ["cloud-platform"]
  }
  metadata = {
    enable-oslogin = "TRUE"
    # Re-runs every boot: format once, mount, fetch the root password, (re)start SurrealDB.
    startup-script = <<-EOT
      #!/bin/bash
      set -euo pipefail
      disk=/dev/disk/by-id/google-surreal-data mount=/mnt/disks/surreal
      blkid "$disk" || mkfs.ext4 -F "$disk"
      mkdir -p "$mount"
      mountpoint -q "$mount" || mount -o discard,defaults "$disk" "$mount"
      meta=http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token
      token=$(curl -sf -H 'Metadata-Flavor: Google' "$meta" | sed -E 's/.*"access_token":"([^"]+)".*/\1/')
      secret=https://secretmanager.googleapis.com/v1/projects/${var.project_id}/secrets/surreal-password/versions/latest:access
      export SURREAL_PASS=$(curl -sf -H "Authorization: Bearer $token" "$secret" | tr -d '\n ' | sed -E 's/.*"data":"([^"]+)".*/\1/' | base64 -d)
      docker rm -f surrealdb || true
      docker run -d --name surrealdb --restart always --user 0:0 -p 8000:8000 \
        -v "$mount":/data -e SURREAL_USER=root -e SURREAL_PASS \
        surrealdb/surrealdb:v3.3.0 start surrealkv:/data/database
    EOT
  }
  depends_on = [google_compute_router_nat.nat, google_secret_manager_secret_iam_member.surreal_vm]
}
