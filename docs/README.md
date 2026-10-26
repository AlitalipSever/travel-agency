# Travel agency documentation

| Document | What it answers |
|---|---|
| [01-requirements.md](01-requirements.md) | What the brief asks for, how it is decomposed, which gaps we fill with assumptions |
| [02-architecture.md](02-architecture.md) | How the system is built: arc42 structure, C4 diagrams, containers, data flow, quality goals |
| [adr/](adr/README.md) | Each significant decision with its context, options and consequences |
| [03-data-model.md](03-data-model.md) | Entities, relations, derived values, indexes |
| [04-api.md](04-api.md) | Endpoint list, request and response shapes, error format, auth |
| [05-work-packages.md](05-work-packages.md) | The work cut into packages as for a team of three, with dependencies and order |
| [06-operations.md](06-operations.md) | Runbook: deploy, rollback, backups, secrets, health, what to look at when something is wrong |
| [07-roadmap.md](07-roadmap.md) | What is done, what was deliberately left out, what the next two weeks would bring |
| [08-walkthrough.md](08-walkthrough.md) | The ten minute walkthrough of the system, in order |

Conventions: arc42 headings for architecture, C4 levels for diagrams (context, container,
component), ADRs in the MADR style. Diagrams are kept as Mermaid in the markdown and rendered
in the case study site.

Status of each document is in its first lines: draft, reviewed, final.
