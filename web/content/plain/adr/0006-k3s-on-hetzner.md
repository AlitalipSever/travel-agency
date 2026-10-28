# 0006 Deploy on k3s on one Hetzner server with one Helm chart; cloud independence over managed services

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: N5

## Context

The system should run for real, be reproducible from code, and cost little.

The stated stack mentions Azure or AWS. We also want the deployment to be portable: the same
artefact on a laptop, on a cheap server, on a managed Kubernetes.

## Options

1. Azure Container Apps with managed PostgreSQL and Redis. Closest to a typical Azure setup,
   with the least operations. But the highest cost and provider coupling, and no Kubernetes
   artefacts.
2. AKS with managed PostgreSQL and Redis. Kubernetes artefacts, Azure alignment, and a managed
   control plane. The cost is the node pool plus the managed services.
3. k3s on one Hetzner ARM server. PostgreSQL and Redis run inside the cluster. Terraform
   handles the server, Helm everything above it. Cheapest and fully reproducible, but all
   operations are ours.

## Decision

Option 3 for this deployment. Option 2 is kept as a values file (`values-azure.yaml`) and
documented.

The application depends only on PostgreSQL, Redis, S3 compatible storage and OpenTelemetry.
So the chart moves between the three options without code changes.

k3s is a certified Kubernetes distribution. What differs from AKS is who operates the control
plane. That difference is understood and accepted for a single node.

## Consequences

- Terraform (hcloud provider) creates the server, firewall and volume, and installs k3s via
  cloud-init.
- ingress-nginx and cert-manager terminate HTTPS.
- No high availability: one node, one disk. This is named in the roadmap, with the step that
  removes it.
- Running the chart on kind locally is part of the definition of done for the chart.
