# 0009 Images in GitHub Container Registry, built by GitHub Actions for arm64 and amd64

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: N5

## Context

Images must be built reproducibly. The cluster must be able to pull them.

The machines involved use two different CPU architectures:

- The server is ARM (Hetzner CAX).
- Developer machines are ARM Macs.
- CI runners are amd64.
- A future AKS pool is amd64.

## Options

1. Docker Hub: it has pull limits, and the free plan allows only one private repository.
2. GitHub Container Registry (ghcr.io): it sits next to the code. It is free for public images
   and generous for private ones. Actions can push to it natively with `GITHUB_TOKEN`.
3. A registry inside the cluster: more to operate, for no gain here.

## Decision

Option 2. The pipeline works like this:

- Actions builds with buildx for `linux/arm64` and `linux/amd64`.
- It tags each image with the commit SHA, and with `latest` on main.
- It pushes to ghcr.io.
- It then runs `helm upgrade` against the cluster.

While the repository is private, the cluster pulls with an image pull secret. Old image
versions are pruned to the last ten.

## Consequences

There is one pipeline file. Multi-arch images let the same chart run on kind (arm64), on the
server (arm64) and on AKS (amd64).
