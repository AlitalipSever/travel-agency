# 0007 PostgreSQL through the CloudNativePG operator

Status: proposed
Date: 2026-10-26
Addresses: N5

## Context

With no managed database (0006), PostgreSQL runs inside the cluster. It needs backups, a
restore path and a route to replication later.

## Options

1. A plain Helm chart (single pod, persistent volume): quick; backups, upgrades and
   replication are manual work.
2. CloudNativePG operator: declarative cluster, scheduled base backups and WAL archiving to
   S3 compatible storage, point in time recovery, rolling minor upgrades, replicas by changing
   one number.
3. A managed PostgreSQL outside the cluster (Neon, Supabase and the like): no operations, but
   reintroduces an external dependency.

## Decision

Option 2. On one node it behaves like option 1, but backups and restore come with it and the
step to two instances is configuration. The learning cost is accepted; if the operator is not
running cleanly within the first working day, fall back to option 1 and record it.

## Consequences

Backups to Hetzner Object Storage, 14 day retention; a restore drill before go-live. Database
credentials are owned by the operator's secret. Application connects through the operator's
read write service.
