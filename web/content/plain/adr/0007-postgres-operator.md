# 0007 PostgreSQL through the CloudNativePG operator

Status: accepted (2026-10-27); fallback taken 2026-10-28 (see Consequences)
Date: 2026-10-26
Addresses: N5

## Context

With no managed database (0006), PostgreSQL runs inside the cluster.

It needs:

- backups;
- a restore path;
- a route to replication later.

## Options

1. A plain Helm chart (single pod, persistent volume). Quick, but backups, upgrades and
   replication are manual work.
2. CloudNativePG operator:
   - declarative cluster;
   - scheduled base backups and WAL archiving to S3 compatible storage;
   - point in time recovery;
   - rolling minor upgrades;
   - replicas by changing one number.
3. A managed PostgreSQL outside the cluster (Neon, Supabase and the like). No operations, but
   it reintroduces an external dependency.

## Decision

Option 2. On one node it behaves like option 1. But backups and restore come with it, and the
step to two instances is configuration.

The learning cost is accepted. If the operator is not running cleanly within the first working
day, fall back to option 1 and record it.

## Consequences

2026-10-28: the fallback clause applied.

- The first release ran a plain PostgreSQL StatefulSet on the Hetzner data volume
  (`postgres.mode: builtin` in the chart), because the operator did not fit the day.
- The chart keeps `postgres.mode: cnpg` as the next step.
- The application does not notice the difference (`DATABASE_URL` only).
- Until then there is no automated backup.

Backups to Hetzner Object Storage, 14 day retention. A restore drill before go-live.
Database credentials are owned by the operator's secret. The application connects
through the operator's read write service.
