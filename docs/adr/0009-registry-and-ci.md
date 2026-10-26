# 0009 Images in GitHub Container Registry, built by GitHub Actions for arm64 and amd64

Status: proposed
Date: 2026-10-26
Addresses: N5

## Context

Images must be built reproducibly and pulled by the cluster. The server is ARM (Hetzner CAX),
developer machines are ARM Macs, CI runners are amd64, a future AKS pool is amd64.

## Options

1. Docker Hub: pull limits, one private repository on the free plan.
2. GitHub Container Registry (ghcr.io): next to the code, free for public images, generous
   for private ones, native `GITHUB_TOKEN` push from Actions.
3. A registry inside the cluster: more to operate for no gain here.

## Decision

Option 2. Actions builds with buildx for `linux/arm64` and `linux/amd64`, tags with the commit
SHA and `latest` on main, pushes to ghcr.io, then runs `helm upgrade` against the cluster. The
cluster pulls with an image pull secret while the repository is private. Old image versions are
pruned to the last ten.

## Consequences

One pipeline file. Multi-arch images let the same chart run on kind (arm64), the server
(arm64) and AKS (amd64).
