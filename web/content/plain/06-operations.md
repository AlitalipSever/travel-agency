# 06 Operations runbook

Status: reviewed against 01 to 05, 2026-10-27.

Commands are the `make` targets the repository will provide. "Recorded" means a dated line in
the tables of this file.

## 1. Environments

| Name | Where | Enter | Values | URL |
|---|---|---|---|---|
| compose | laptop, Docker | `make up`, `make test`, `make seed`, `make demo` | `.env` from `.env.example` | http://localhost:8000 (api), http://localhost:3000 (web) |
| kind (planned, L2) | laptop, Kubernetes in Docker | `helm upgrade --install … -f chart/values-local.yaml` | `chart/values-local.yaml` | http://localhost (ingress), no TLS |
| hetzner (live since 2026-10-28) | one CAX21, k3s (`infra/terraform`) | `export KUBECONFIG=~/.kube/travel-agency.yaml`; `make images-push`, `make deploy TAG=<sha>` | `chart/values-hetzner.yaml` | https://travel-agency.asever.dev |
| azure | AKS, documented profile only | | `chart/values-azure.yaml` | |

- **hetzner:** the name is in Cloudflare DNS as an A record, DNS only.

## 2. Deploy

Trigger: push to `main` (pull requests run tests only).

1. CI gates: ruff, mypy, pytest (with PostgreSQL and Redis services), squawk on migrations,
   dependency scan. Any red stops the chain.
2. Images: `api` and `web`, buildx `linux/arm64,linux/amd64`. The tag = commit SHA (+ `latest`
   on main). They are pushed to ghcr.io.
3. Release: `helm upgrade --install travel-agency chart/ -f chart/values-hetzner.yaml --set
   image.tag=<sha>`. It uses a deploy kubeconfig held as a GitHub secret.
4. Inside Helm, the **migrate job** runs first as a pre-upgrade hook (`migrate` + idempotent
   seed). If it fails, the release is not applied and the old version keeps running. Then come
   rolling updates: api (2 replicas, readiness gated), worker, beat, web.
5. Smoke test: `/readyz` is 200 and one bookable query is 200. On failure, CI runs
   `helm rollback` and fails the job.
6. What is live: `helm history travel-agency` (revision, SHA, time) and `/api/v1/ops/status`
   (`versions.commit`).

Manual deploy from a laptop: `make images-push TAG=<sha>` then `make deploy TAG=<sha>` (steps 2
to 4).

- This is how the first ten revisions went out on 2026-10-28.
- The arm64 build is native on an Apple Silicon laptop (about five minutes).
- The QEMU build in CI (QEMU emulates the arm64 CPU) runs only on `main`.
- Step 5 (CI smoke test and automatic rollback) and the `helm upgrade` from CI are P6b, still
  open.

Before the first release, the cluster is prepared once (P1, P2):

- `make infra-apply` creates the server (Terraform, `infra/terraform`).
- The A record is set by hand in Cloudflare.
- `make bootstrap` installs ingress-nginx, cert-manager and the two Let's Encrypt
  `ClusterIssuer`s (`infra/k8s`).

Certificates are requested through the Ingress annotation `cert-manager.io/cluster-issuer`:

- `letsencrypt-staging` first: unlimited, browser-untrusted, checked with `curl -k`.
- Then `letsencrypt-prod`: 5 certificates per name per week.

Done 2026-10-28 with the temporary hello page (`make hello-up`). `make hello-down` removes it
once the chart serves the host.

Migration policy (expand-contract):

- Add first (nullable or defaulted columns, new tables).
- Keep the code working with both shapes.
- Remove in a later release.

A rollback therefore never needs a down migration. Index creation uses `CONCURRENTLY`; squawk
(a linter for migrations) enforces the rest.

## 3. Rollback

```
helm history travel-agency
helm rollback travel-agency <revision>
```

This rolls the images back. The schema stays (see the migration policy).

Afterwards, check `/readyz`, one bookable query and `kubectl get pods -n travel-agency`. Record
the rollback in §11.

## 4. Secrets and access

| Secret | Holds | Created by | Rotation |
|---|---|---|---|
| `travel-agency-app` | Django secret key, OpenWeatherMap API key, Redis password, agency defaults | `make secrets` | Replace the Secret, `kubectl rollout restart deploy -n travel-agency` |
| `travel-agency-db-app` | PostgreSQL user and password for the application | CloudNativePG, automatically | Operator managed |
| `ghcr-pull` | Image pull token for ghcr.io while the repository is private | `make secrets` | New token in GitHub, replace the Secret |
| `backup-s3` | Object Storage key for CloudNativePG backups | `make secrets` | Replace, operator picks it up |
| GitHub Actions: `KUBECONFIG_DEPLOY`, `GHCR_TOKEN` | Deploy access and image push | Operator, in the repository settings | Rotate in the cluster and GitHub together |

- **`travel-agency-app`:** `make secrets` prompts, writes the Secret, and keeps nothing on disk.

API tokens for people and partners:

- Operations creates the user in the admin (role, partner) and issues the DRF token there.
- There is no login endpoint.
- The site reads the demo partner's token at build time from its environment.
- Rotating it means rotating the Secret and rebuilding `web`.

These stay on the operator's machine and are ignored by git:

- Terraform state (`infra/terraform/terraform.tfstate`);
- `terraform.tfvars` (operator IP);
- the Hetzner token (`infra/terraform/.env`, read as `HCLOUD_TOKEN`).

The token is needed only when the infrastructure changes.

Access:

- The kubeconfig and SSH key exist only on the operator's machine and in GitHub secrets.
- SSH is key based and limited to the operator's IPs by the firewall.
- Nobody has database credentials outside the cluster (use `kubectl cnpg psql` when needed).

## 5. Backups and restore

Targets (Q5): RPO one night, RTO 30 minutes. RPO is how much data may be lost; RTO is how long
a restore may take.

- CloudNativePG: nightly base backup plus continuous WAL archiving to Hetzner Object Storage.
  WAL is the database's write-ahead log. Retention is 14 days. `kubectl get backups -n
  travel-agency` lists them.
- Restore drill: `make restore-drill` creates a second cluster from the latest backup. It runs
  a migrations check and a row count comparison per table, then deletes the cluster. Run it
  before go-live and after any change to the backup configuration. Record it below.
- Local rehearsal (L3): the kind profile backs up to a MinIO pod with the same settings. So the
  drill is practised before the server exists.
- Full loss: `terraform apply` (server), `make bootstrap` (add-ons, secrets), `make deploy`.
  Then restore the cluster from Object Storage with the CloudNativePG `recovery` bootstrap.

| Date | Drill | Duration | Result |
|---|---|---|---|
| | | | |

## 6. Routine checks

| When | Check | Where |
|---|---|---|
| Daily (automated) | Nightly backup succeeded; demo reset ran; retention ran | `kubectl get backups`, `RefreshRun` and task logs, `/ops/status` |
| Daily (glance) | Upstream calls against shares, breaker closed, last refresh recent, `no_data` empty | `/ops/status`, brackets endpoint |
| Weekly | Certificate renewal state, disk on the data volume, pod restarts, error rate | `kubectl describe certificate`, `df` on the volume, `kubectl get pods`, metrics |
| Monthly | Dependency updates (Dependabot), image rebuild, review of history table growth | GitHub, CI, `psql` |

- **Monthly:** the image rebuild picks up tzdata and base image patches.

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
| Refresh interval | env `REFRESH_INTERVAL_S` | 900 | Beat schedule |
| Budget shares | env `UPSTREAM_REFRESH_SHARE`, `UPSTREAM_ADHOC_SHARE` | 40, 8 per minute (sum under 80 % of 60) | Bulkhead between refresh and ad hoc calls |
| Ad hoc rate limit | env `ADHOC_RATE_PER_MIN` | 30 per token | 429 past it |
| api replicas, resources | `values-*.yaml` | 2; see 02 §7.2 | Capacity |
| Breaker thresholds | env `BREAKER_FAILURES`, `BREAKER_COOLDOWN_S` | 5, 60 | When the adapter stops calling upstream |
| `DJANGO_SECURE_SSL_REDIRECT` | chart ConfigMap | `false` in the cluster (`true` is the image default) | HTTPS is enforced by ingress-nginx |

- **Refresh interval:** the task lengthens it when the budget would be exceeded. It reports
  the effective value.
- **Budget shares:** a bulkhead keeps one kind of call from using up the other's budget.
- **`DJANGO_SECURE_SSL_REDIRECT`:**
  - In-cluster probes and the web pod use plain http.
  - Django still treats proxied requests as secure through `X-Forwarded-Proto`.
  - nginx sets that header itself (`use-forwarded-headers: false`).

## 9. Health and observability

- `/healthz`: process up (liveness). `/readyz`: database and Redis reachable (readiness).
- `/api/v1/ops/status` shows:
  - the last `RefreshRun` (trigger, locations, calls, failures, effective interval);
  - calls this minute and this month against the shares;
  - breaker state;
  - ad hoc cache hit ratio;
  - sample count;
  - versions (api, chart, commit).
- Logs: JSON with `request_id`, `user`, `partner`, `path`, `status`, `duration_ms`. Read them
  with `kubectl logs deploy/api -n travel-agency`, `deploy/worker`, `deploy/beat`.
- Metrics: `/metrics` (RED per endpoint, upstream calls, shares, breaker). RED means rate,
  errors and duration. They are scraped when P7 is installed; otherwise read them through
  `/ops/status`.

## 10. When something is wrong

| Symptom | Look at | Likely cause and action |
|---|---|---|
| Weather answers `source: stale` | `/ops/status` breaker and calls; worker logs | Upstream down or rate limiting |
| Weather returns 503 | same, plus whether the coordinate is ad hoc | Upstream down and nothing stored for that coordinate |
| 429 on ad hoc weather | `/ops/status` ad hoc share; caller's token | Caller over its limit or the ad hoc share exhausted |
| Brackets show many locations in `no_data` | beat and worker pods; `RefreshRun` failures | Beat not running, queue stuck, or new locations before their first refresh |
| Effective refresh interval longer than configured | location count; shares | Budget rule lengthened it (W4.2) |
| 409 on every booking of a departure | departure capacity and confirmed seats | Sold out; or capacity lowered |
| Partner reports missing bookings | the user's `partner_id` | Bookings belong to another partner by design (scope) |
| History rows without an actor | pghistory middleware in the API, task context in the worker | Context not set on that path |
| Certificate warning or HTTP only | `kubectl describe certificate`, `describe order`, DNS | Challenge failed |
| Certificate issued by "(STAGING) Let's Encrypt" | `kubectl get ingress -o yaml`, the issuer annotation | Switch the annotation to `letsencrypt-prod` |
| Pods `ImagePullBackOff` | `kubectl describe pod` | ghcr pull secret expired or image tag missing |
| `CrashLoopBackOff` after a deploy | migrate job logs, `helm history` | Migration or config failed; `helm rollback` |
| Two refreshes per interval | `kubectl get deploy beat` replicas | A second beat; scale to 1 |
| Days mis-assigned around a DST change | image build date, tzdata version | Stale tz data; rebuild the image |
| Data volume filling | `df`, sample and history counts | Retention not running, or history growth |
| Demo always sold out or empty | demo reset task logs | Nightly reset failed; `make demo-reset` |

- **`source: stale`:** wait for the breaker to close, check the API key.
- **503:** known locations are unaffected.
- **429:** raise shares only if the refresh share has room.
- **Longer refresh interval:** fewer locations or a paid tier.
- **409 on every booking:** check history for the change.
- **History rows without an actor:** fix the middleware or the task wrapper.
- **Certificate warning or HTTP only:** likely causes are DNS not pointing, port 80 closed,
  staging issuer still selected, or a Let's Encrypt rate limit.
- **"(STAGING) Let's Encrypt" certificate:** after switching the annotation, delete the TLS
  Secret and apply again. cert-manager reissues within a minute.
- **Data volume filling:** run retention, plan a bigger volume.

## 11. Incidents and changes log

Record here rollbacks, restores, outages and manual interventions. One line each:

- date;
- what happened;
- what was done;
- follow-up (an ADR, a roadmap item or a test).

| Date | Event | Action | Follow-up |
|---|---|---|---|
| | | | |

## 12. Time zone data

The application image updates the `tzdata` system package and Python's `tzdata` wheel on every
build. This is because daylight saving rules change (F4).

The monthly rebuild in §6 exists for this and for base image patches.

## 13. Costs (estimates, confirmed once live)

| Item | Monthly |
|---|---|
| Hetzner CAX21 (ARM, 4 vCPU, 8 GB) | about 7 EUR |
| Data volume (20 GB) | under 1 EUR |
| Object Storage (backups, a few GB) | under 1 EUR |
| Domain | about 1 EUR (10 to 15 EUR a year) |
| ghcr.io, GitHub Actions, Let's Encrypt, Cloudflare DNS | 0 within free allowances |
| Total | about 10 EUR |
