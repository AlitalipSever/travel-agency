# One Hetzner server running k3s, its firewall and a data volume (05-work-packages P1,
# 02-architecture deployment view). Everything the server needs at first boot is in
# cloud-init.yaml. Run from this directory with HCLOUD_TOKEN in the environment.

terraform {
  required_version = ">= 1.6"

  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.49"
    }
  }
}

# The token comes from HCLOUD_TOKEN; nothing is configured here on purpose.
provider "hcloud" {}

locals {
  labels = {
    project = "travel-agency"
    managed = "terraform"
  }
}

# The operator's public key, read from disk and registered in the project so the server
# trusts it from the first boot.
resource "hcloud_ssh_key" "operator" {
  name       = "${var.server_name}-operator"
  public_key = file(pathexpand(var.ssh_public_key_path))
  labels     = local.labels
}

# Administrative ports only from the operator's address; web ports from everywhere.
resource "hcloud_firewall" "server" {
  name   = var.server_name
  labels = local.labels

  rule {
    description = "SSH from the operator"
    direction   = "in"
    protocol    = "tcp"
    port        = "22"
    source_ips  = [var.operator_cidr]
  }

  rule {
    description = "Kubernetes API from the operator"
    direction   = "in"
    protocol    = "tcp"
    port        = "6443"
    source_ips  = [var.operator_cidr]
  }

  rule {
    description = "HTTP (ACME challenge, redirect to HTTPS)"
    direction   = "in"
    protocol    = "tcp"
    port        = "80"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }

  rule {
    description = "HTTPS"
    direction   = "in"
    protocol    = "tcp"
    port        = "443"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }

  rule {
    description = "ICMP (ping, path MTU)"
    direction   = "in"
    protocol    = "icmp"
    source_ips  = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_server" "k3s" {
  name         = var.server_name
  server_type  = var.server_type
  location     = var.location
  image        = var.image
  ssh_keys     = [hcloud_ssh_key.operator.id]
  firewall_ids = [hcloud_firewall.server.id]
  labels       = local.labels

  # Rendered once at creation; k3s and the data mount are set up by this script.
  user_data = templatefile("${path.module}/cloud-init.yaml", {
    k3s_version = var.k3s_version
  })

  public_net {
    ipv4_enabled = true
    ipv6_enabled = true
  }

  backups            = false
  delete_protection  = true
  rebuild_protection = true

  lifecycle {
    # cloud-init runs only on first boot; a changed script must not recreate the server.
    ignore_changes = [user_data]
  }
}

# Separate disk for PostgreSQL so the server can be rebuilt without losing data.
resource "hcloud_volume" "data" {
  name     = "${var.server_name}-data"
  size     = var.volume_size_gb
  location = var.location
  format   = "ext4"
  labels   = local.labels

  delete_protection = true
}

resource "hcloud_volume_attachment" "data" {
  volume_id = hcloud_volume.data.id
  server_id = hcloud_server.k3s.id
  automount = false
}
