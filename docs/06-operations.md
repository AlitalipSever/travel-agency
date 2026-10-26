# 06 Operations runbook

Status: draft, 2026-10-26. Filled in as each piece goes live.

## Environments

| Name | Where | Values file | URL |
|---|---|---|---|
| local | kind on a laptop | `chart/values-local.yaml` | http://localhost |
| hetzner | k3s, one ARM server | `chart/values-hetzner.yaml` | https://travel-agency.<domain> |
| azure | AKS (documented, not run) | `chart/values-azure.yaml` | |

## Deploy

Push to `main`. CI runs lint and tests, builds arm64 and amd64 images, pushes to ghcr.io with
the commit SHA as tag, runs `helm upgrade --install` with that tag. The migrate job runs before
the api rollout. Manual: `make deploy TAG=<sha>`.

## Rollback

`helm rollback travel-agency <revision>`; `helm history travel-agency` lists revisions. Migrations are
written to be backward compatible for one version so that rollback does not need a down
migration.

## Secrets

Kubernetes Secrets in the `travel-agency` namespace: database credentials (owned by CloudNativePG),
Redis password, OpenWeatherMap key, Django secret key, ghcr pull secret. Created once by hand
(`make secrets`), never in values files or git. Rotation: replace the secret, restart the
deployment.

## Backups

CloudNativePG schedules a nightly base backup plus WAL archiving to Hetzner Object Storage,
retention 14 days. Restore drill: `make restore-drill` creates a second cluster from the
latest backup and runs a row count comparison. Done once before go-live, result noted here.

## Health

- `/healthz` process, `/readyz` dependencies. Kubernetes probes use both.
- `/api/v1/ops/status`: cache hit ratio, last refresh, upstream budget used, versions.
- `kubectl get pods -n travel-agency`, `kubectl logs deploy/api -n travel-agency`.

## When something is wrong

| Symptom | Look at | Likely |
|---|---|---|
| Weather endpoints return `stale` | worker logs, upstream status | OpenWeatherMap down or key over budget |
| Brackets page empty | beat and worker pods, Redis | Scheduler not running or cache flushed |
| 409 on every booking | departure capacity, bookings table | Sold out, or a stuck transaction |
| Certificate warning | `kubectl describe certificate -n travel-agency` | cert-manager challenge failed, DNS not pointing |
| Pod CrashLoopBackOff after deploy | migrate job logs | Migration failed; rollback |

## Costs

One ARM server, one volume, object storage, a domain. Listed with amounts once live.
