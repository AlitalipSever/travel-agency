# Inputs for the Hetzner server that runs k3s (05-work-packages P1).
# Values that differ per operator (the allowed IP range) live in terraform.tfvars, which git
# ignores. The Hetzner API token is never a variable: the provider reads HCLOUD_TOKEN from
# the environment.

variable "server_name" {
  description = "Name of the server in Hetzner Cloud; also its hostname."
  type        = string
  default     = "travel-agency"
}

variable "server_type" {
  description = "Hetzner server type. cax21 = 4 ARM vCPU, 8 GB RAM (02-architecture 7.2)."
  type        = string
  default     = "cax21"
}

variable "location" {
  description = "Hetzner location: fsn1 (Falkenstein), nbg1 (Nuremberg) or hel1 (Helsinki)."
  type        = string
  default     = "fsn1"
}

variable "image" {
  description = "Operating system image; an LTS that k3s supports."
  type        = string
  default     = "ubuntu-24.04"
}

variable "volume_size_gb" {
  description = "Size of the data volume mounted for PostgreSQL, in GB."
  type        = number
  default     = 20
}

variable "ssh_public_key_path" {
  description = "Path to the operator's SSH public key; uploaded to Hetzner and installed on the server."
  type        = string
  default     = "~/.ssh/travel-agency-hetzner.pub"
}

variable "operator_cidr" {
  description = "IP range allowed to reach SSH (22) and the Kubernetes API (6443), e.g. 203.0.113.7/32."
  type        = string

  validation {
    condition     = can(cidrhost(var.operator_cidr, 0))
    error_message = "operator_cidr must be a CIDR such as 203.0.113.7/32."
  }
}

variable "k3s_version" {
  description = "k3s release installed by cloud-init; pinned so a rebuild gives the same cluster."
  type        = string
  default     = "v1.31.6+k3s1"
}
