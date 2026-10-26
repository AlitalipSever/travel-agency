# 07 Roadmap

Status: draft, 2026-10-26. Three lists, kept honest: what is done, what was left out on
purpose, what comes next.

## Done

Filled in as packages close (see 05-work-packages.md).

## Deliberately left out

| Item | Why | What it would take |
|---|---|---|
| Event streaming (Kafka) | No requirement needs an event bus yet; the refresh job and bookings are fine as tasks and transactions | Outbox table, a producer in the booking service, a consumer for notifications; Event Hubs or Redpanda in the chart |
| High availability | One server is enough for the brief; HA is a platform step, not an application change | Second node, PostgreSQL with two instances, api replicas spread by anti affinity |
| Payments, accounts, password flows | Out of the brief; large surface | A payment provider adapter and a customer identity model |
| Multi tenancy | One agency in the brief | Tenant id on every table, row level security |
| Unit systems other than metric | Celsius is natural for the agency and its markets (A14) | A `units` query parameter converting at the edge |
| Traveller self-service (role, booking UI) | The brief asks for a system that runs the agency; travellers book through staff and partners (00-domain §2) | A `traveller` role with registration, login and password flows, own-bookings scope, GDPR access and erasure endpoints, and a front end |

## Next two weeks, if this continued

1. Restore drill and a written RPO/RTO.
2. Outbox and domain events for bookings; a notification consumer.
3. Rate limiting and quotas on the public API.
4. Second node and PostgreSQL replica; load test with k6 and the numbers in this file.
5. A "same day last week" comparison on the brackets page, from the persisted weather samples.
6. Contract tests against the OpenAPI schema; generated TypeScript client for the site.

## How this grows with a larger team

Module boundaries follow the Django apps: weather, locations, catalogue, booking. Each can be
owned by one pair, each has its own tests and its own section in the ADR log. The chart stays
one; values files multiply per environment. The first split into separate services would be the
weather adapter, since its load profile (scheduled, upstream bound) differs from the API's.
