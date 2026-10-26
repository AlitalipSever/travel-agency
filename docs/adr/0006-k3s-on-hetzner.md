# 0006 Deploy on k3s on one Hetzner server with one Helm chart; cloud independence over managed services

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: N5

## Context

The system should run for real, be reproducible from code, and cost little. The stated stack
mentions Azure or AWS. We also want the deployment to be portable: the same artefact on a
laptop, on a cheap server, on a managed Kubernetes.

## Options

1. Azure Container Apps with managed PostgreSQL and Redis: closest to a typical Azure setup,
   least operations, highest cost and provider coupling, no Kubernetes artefacts.
2. AKS with managed PostgreSQL and Redis: Kubernetes artefacts, Azure alignment, control
   plane managed; cost of node pool plus managed services.
3. k3s on one Hetzner ARM server, PostgreSQL and Redis inside the cluster, Terraform for the
   server, Helm for everything above it: cheapest, fully reproducible, all operations ours.

## Decision

Option 3 for this deployment, with option 2 kept as a values file (`values-azure.yaml`) and
documented. The application depends only on PostgreSQL, Redis, S3 compatible storage and
OpenTelemetry, so the chart moves between the three options without code changes. k3s is a
certified Kubernetes distribution; what differs from AKS is who operates the control plane,
and that difference is understood and accepted for a single node.

## Consequences

Terraform (hcloud provider) creates server, firewall, volume and installs k3s via cloud-init.
ingress-nginx and cert-manager terminate HTTPS. No high availability: one node, one disk;
named in the roadmap with the step that removes it. Running the chart on kind locally is part
of the definition of done for the chart.
