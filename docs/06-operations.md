# 06 Operations runbook

Status: reviewed against 01 to 05, 2026-10-27. Commands are the `make` targets the repository
will provide; "recorded" means a dated line in the tables of this file.

## 1. Environments

| Name | Where | Enter | Values | URL |
|---|---|---|---|---|
| compose | laptop, Docker | `make up`, `make test`, `make seed`, `make demo` | `.env` from `.env.example` | http://localhost:8000 (api), http://localhost:3000 (web) |
| kind | laptop, Kubernetes in Docker | `make kind-up`, `make kind-deploy`, `make kind-down` | `chart/values-local.yaml` | http://localhost (ingress), no TLS |
| hetzner | one CAX21, k3s (`infra/terraform`) | `export KUBECONFIG=~/.kube/travel-agency.yaml`; `make deploy TAG=<sha>` | `chart/values-hetzner.yaml` | `https://travel-agency.<domain>` (Cloudflare DNS, A record, DNS only) |
| azure | AKS, documented profile only | | `chart/values-azure.yaml` | |

## 2. Deploy

Trigger: push to `main` (pull requests run tests only).

1. CI gates: ruff, mypy, pytest (with PostgreSQL and Redis services), squawk on migrations,
   dependency scan. Any red stops the chain.
2. Images: `api` and `web`, buildx `linux/arm64,linux/amd64`, tag = commit SHA (+ `latest`
   on main), pushed to ghcr.io.
3. Release: `helm upgrade --install travel-agency chart/ -f chart/values-hetzner.yaml --set
   image.tag=<sha>` with a deploy kubeconfig held as a GitHub secret.
4. Inside Helm: the **migrate job** runs as a pre-upgrade hook (`migrate` + idempotent seed);
   if it fails the release is not applied and the old version keeps running. Then rolling
   updates: api (2 replicas, readiness gated), worker, beat, web.
5. Smoke test: `/readyz` is 200 and one bookable query is 200; on failure CI runs
   `helm rollback` and fails the job.
6. What is live: `helm history travel-agency` (revision, SHA, time) and `/api/v1/ops/status`
   (`versions.commit`).

Manual deploy from a laptop: `make deploy TAG=<sha>` (same steps 3 to 5).

Before the first release the cluster is prepared once (P1, P2): `make infra-apply` creates the
server (Terraform, `infra/terraform`), the A record is set by hand in Cloudflare, and
`make bootstrap` installs ingress-nginx, cert-manager and the two Let's Encrypt
`ClusterIssuer`s (`infra/k8s`). Certificates are requested through the Ingress annotation
`cert-manager.io/cluster-issuer`: `letsencrypt-staging` first (unlimited, browser-untrusted,
checked with `curl -k`), then `letsencrypt-prod` (5 certificates per name per week). Done
2026-10-28 with the temporary hello page (`make hello-up`), which `make hello-down` removes
once the chart serves the host.

Migration policy (expand-contract): add first (nullable or defaulted columns, new tables),
keep the code working with both shapes, remove in a later release. A rollback therefore never
needs a down migration. Index creation uses `CONCURRENTLY`; squawk enforces the rest.

## 3. Rollback

```
helm history travel-agency
helm rollback travel-agency <revision>
```

Rolls the images back; the schema stays (see the migration policy). Afterwards: `/readyz`, one
bookable query, `kubectl get pods -n travel-agency`. Record the rollback in §11.

## 4. Secrets and access

| Secret | Holds | Created by | Rotation |
|---|---|---|---|
| `travel-agency-app` | Django secret key, OpenWeatherMap API key, Redis password, agency defaults | `make secrets` (prompts, writes the Secret, nothing on disk) | Replace the Secret, `kubectl rollout restart deploy -n travel-agency` |
| `travel-agency-db-app` | PostgreSQL user and password for the application | CloudNativePG, automatically | Operator managed |
| `ghcr-pull` | Image pull token for ghcr.io while the repository is private | `make secrets` | New token in GitHub, replace the Secret |
| `backup-s3` | Object Storage key for CloudNativePG backups | `make secrets` | Replace, operator picks it up |
| GitHub Actions: `KUBECONFIG_DEPLOY`, `GHCR_TOKEN` | Deploy access and image push | Operator, in the repository settings | Rotate in the cluster and GitHub together |

API tokens for people and partners: operations creates the user in the admin (role, partner)
and issues the DRF token there; there is no login endpoint. The demo partner's token is read by
the site at build time from its environment; rotating it means rotating the Secret and
rebuilding `web`.

Terraform state (`infra/terraform/terraform.tfstate`), `terraform.tfvars` (operator IP) and the
Hetzner token (`infra/terraform/.env`, read as `HCLOUD_TOKEN`) stay on the operator's machine and
are ignored by git; the token is needed only when the infrastructure changes.

Access: kubeconfig and SSH key only on the operator's machine and in GitHub secrets; SSH is
key based and limited to the operator's IPs by the firewall; nobody has database credentials
outside the cluster (use `kubectl cnpg psql` when needed).

## 5. Backups and restore

Targets (Q5): RPO one night, RTO 30 minutes.

- CloudNativePG: nightly base backup plus continuous WAL archiving to Hetzner Object Storage,
  retention 14 days. `kubectl get backups -n travel-agency` lists them.
- Restore drill: `make restore-drill` creates a second cluster from the latest backup, runs
  migrations check and a row count comparison per table, then deletes it. Run before go-live
  and after any change to the backup configuration; record below.
- Local rehearsal (L3): the kind profile backs up to a MinIO pod with the same settings, so the
  drill is practised before the server exists.
- Full loss: `terraform apply` (server), `make bootstrap` (add-ons, secrets), `make deploy`,
  then restore the cluster from Object Storage with the CloudNativePG `recovery` bootstrap.

| Date | Drill | Duration | Result |
|---|---|---|---|
| | | | |

## 6. Routine checks

| When | Check | Where |
|---|---|---|
| Daily (automated) | Nightly backup succeeded; demo reset ran; retention ran | `kubectl get backups`, `RefreshRun` and task logs, `/ops/status` |
| Daily (glance) | Upstream calls against shares, breaker closed, last refresh recent, `no_data` empty | `/ops/status`, brackets endpoint |
| Weekly | Certificate renewal state, disk on the data volume, pod restarts, error rate | `kubectl describe certificate`, `df` on the volume, `kubectl get pods`, metrics |
| Monthly | Dependency updates (Dependabot), image rebuild for tzdata and base image patches, review of history table growth | GitHub, CI, `psql` |

## 7. Retention

| Data | Kept | Mechanism |
|---|---|---|
| Weather samples | 90 days (`sample_retention_days`) | nightly retention task |
| `RefreshRun` rows | 90 days | same task |
| Backups and WAL | 14 days | CloudNativePG retention policy |
| Demo bookings | one day | nightly demo reset (`make demo-reset` by hand) |
| History tables | unbounded in this iteration | roadmap (GDPR row) |
| Ad hoc weather cache | 10 minutes | Redis TTL |

## 8. Knobs

| Setting | Where | Default | Effect |
|---|---|---|---|
| `bracket_edges` | settings table (API `/locations/bracket-edges`, admin) | [10, 20, 25, 30] | Bracket boundaries, next read |
| `agency_timezone` | settings table | the agency's zone | "Today" for bookability |
| `sample_retention_days` | settings table | 90 | Retention task |
| Refresh interval | env `REFRESH_INTERVAL_S` | 900 | Beat schedule; the task lengthens it when the budget would be exceeded and reports the effective value |
| Budget shares | env `UPSTREAM_REFRESH_SHARE`, `UPSTREAM_ADHOC_SHARE` | 40, 8 per minute (sum under 80 % of 60) | Bulkhead between refresh and ad hoc calls |
| Ad hoc rate limit | env `ADHOC_RATE_PER_MIN` | 30 per token | 429 past it |
| api replicas, resources | `values-*.yaml` | 2; see 02 §7.2 | Capacity |
| Breaker thresholds | env `BREAKER_FAILURES`, `BREAKER_COOLDOWN_S` | 5, 60 | When the adapter stops calling upstream |

## 9. Health and observability

- `/healthz` process up (liveness), `/readyz` database and Redis reachable (readiness).
- `/api/v1/ops/status`: last `RefreshRun` (trigger, locations, calls, failures, effective
  interval), calls this minute and this month against the shares, breaker state, ad hoc cache
  hit ratio, sample count, versions (api, chart, commit).
- Logs: JSON with `request_id`, `user`, `partner`, `path`, `status`, `duration_ms`;
  `kubectl logs deploy/api -n travel-agency`, `deploy/worker`, `deploy/beat`.
- Metrics: `/metrics` (RED per endpoint, upstream calls, shares, breaker) scraped when P7 is
  installed; otherwise read through `/ops/status`.

## 10. When something is wrong

| Symptom | Look at | Likely cause and action |
|---|---|---|
| Weather answers `source: stale` | `/ops/status` breaker and calls; worker logs | Upstream down or rate limiting; wait for the breaker to close, check the API key |
| Weather returns 503 | same, plus whether the coordinate is ad hoc | Upstream down and nothing stored for that coordinate; known locations are unaffected |
| 429 on ad hoc weather | `/ops/status` ad hoc share; caller's token | Caller over its limit or the ad hoc share exhausted; raise shares only if the refresh share has room |
| Brackets show many locations in `no_data` | beat and worker pods; `RefreshRun` failures | Beat not running, queue stuck, or new locations before their first refresh |
| Effective refresh interval longer than configured | location count; shares | Budget rule lengthened it (W4.2); fewer locations or a paid tier |
| 409 on every booking of a departure | departure capacity and confirmed seats | Sold out; or capacity lowered; check history for the change |
| Partner reports missing bookings | the user's `partner_id` | Bookings belong to another partner by design (scope) |
| History rows without an actor | pghistory middleware in the API, task context in the worker | Context not set on that path; fix the middleware or the task wrapper |
| Certificate warning or HTTP only | `kubectl describe certificate`, `describe order`, DNS | Challenge failed: DNS not pointing, port 80 closed, staging issuer still selected, Let's Encrypt rate limit |
| Certificate issued by "(STAGING) Let's Encrypt" | `kubectl get ingress -o yaml`, the issuer annotation | Switch the annotation to `letsencrypt-prod`, delete the TLS Secret, apply again; cert-manager reissues within a minute |
| Pods `ImagePullBackOff` | `kubectl describe pod` | ghcr pull secret expired or image tag missing |
| `CrashLoopBackOff` after a deploy | migrate job logs, `helm history` | Migration or config failed; `helm rollback` |
| Two refreshes per interval | `kubectl get deploy beat` replicas | A second beat; scale to 1 |
| Days mis-assigned around a DST change | image build date, tzdata version | Stale tz data; rebuild the image |
| Data volume filling | `df`, sample and history counts | Retention not running, or history growth; run retention, plan a bigger volume |
| Demo always sold out or empty | demo reset task logs | Nightly reset failed; `make demo-reset` |

## 11. Incidents and changes log

Record rollbacks, restores, outages and manual interventions here, one line each: date, what
happened, what was done, follow-up (an ADR, a roadmap item or a test).

| Date | Event | Action | Follow-up |
|---|---|---|---|
| | | | |

## 12. Time zone data

The application image updates the `tzdata` system package and Python's `tzdata` wheel on
every build, because daylight saving rules change (F4); the monthly rebuild in §6 exists for
this and for base image patches.

## 13. Costs (estimates, confirmed once live)

| Item | Monthly |
|---|---|
| Hetzner CAX21 (ARM, 4 vCPU, 8 GB) | about 7 EUR |
| Data volume (20 GB) | under 1 EUR |
| Object Storage (backups, a few GB) | under 1 EUR |
| Domain | about 1 EUR (10 to 15 EUR a year) |
| ghcr.io, GitHub Actions, Let's Encrypt, Cloudflare DNS | 0 within free allowances |
| Total | about 10 EUR |
