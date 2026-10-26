# 02b Architecture: quality, risks, glossary

Status: draft, 2026-10-26. arc42 sections 10 to 12, split from [02-architecture.md](02-architecture.md)
to keep both files short.

## 10. Quality requirements

### 10.1 Quality requirements overview

`TODO (arc42 10.1)`: quality tree from the four goals in 1.2 down to the scenarios in 10.2.

### 10.2 Quality scenarios

Short form: context, stimulus, response, metric. U = usage scenario, C = change scenario.

| Id | Type | Stimulus | Response | Metric |
|---|---|---|---|---|
| Q1 | U | OpenWeatherMap returns 5xx for 10 minutes | Weather endpoints answer from cache, marked stale; refresh job backs off | 0 upstream-caused 5xx; p95 latency unchanged |
| Q2 | U | 13 locations refreshed every 15 minutes | Within the upstream budget; samples pruned at 90 days | < 5 calls/min of 60; table < 40k rows |
| Q3 | U | Two bookings for the last seat at the same moment | One succeeds, one gets 409 | 0 overbookings in the concurrency test |
| Q4 | U | Deploy a new api version | Rolling update, migrations first | 0 failed requests during rollout |
| Q5 | U | Server lost | Terraform recreates, Helm reinstalls, PostgreSQL restored | restore drill under 30 minutes; RPO one night |
| Q6 | C | Client changes the danger semantics to exact match | One query change, tests updated | under one hour, one ADR |
| Q7 | C | A new weather provider | New adapter behind the same interface | no change outside `weather` |

## 11. Risks and technical debt

| Priority | Risk or debt | Consequence | Measure |
|---|---|---|---|
| 1 | Single node, single disk | Outage on server loss until restored | Backups + restore drill now; second node and replica in the roadmap |
| 2 | Free tier weather data | No history, 3 hour resolution, 120 hour window | Persisted samples (ADR 0012); paid tier if the client needs more |
| 3 | Operator-managed database with one instance | No failover | Two instances is one setting once a second node exists |
| 4 | First day after deployment | Today's summary partial | Stated in the response (`partial`) |

## 12. Glossary

| Term | Definition |
|---|---|
| Departure | A package on one date with its capacity; ends after the package's duration |
| Bookable | Departure in the requested range, in the future, with seats remaining |
| Danger score | 0 none, 1 low, 2 medium, 3 high; a package's score is the max of its destinations |
| Weather sample | One 3 hour forecast slot or one observation for a known location, stored in UTC |
| Local day | The calendar day in the location's IANA zone |

Business terms are defined once in [00-domain.md](00-domain.md) section 4; this table keeps the
technical ones only.
