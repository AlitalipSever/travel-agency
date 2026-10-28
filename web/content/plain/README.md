# Travel agency documentation

| Document | What it answers |
|---|---|
| [00-domain.md](00-domain.md) | Who the system is for: stakeholders, actors, jobs and language (see below) |
| [01-requirements.md](01-requirements.md) | The brief, the writing rules and every requirement (see below) |
| [02-architecture.md](02-architecture.md) | How the system is built: arc42 sections 1 to 12, C4 diagrams (see below) |
| [arc42-checklist.md](arc42-checklist.md) | Every official arc42 subsection, where it lives in 02 and its status |
| [adr/](adr/README.md) | Each significant decision with its context, options and consequences |
| [03-data-model.md](03-data-model.md) | Entities, relations, derived values, indexes |
| [04-api.md](04-api.md) | Endpoint list, request and response shapes, error format, auth |
| [05-work-packages.md](05-work-packages.md) | The work cut into packages as for a team of three, with dependencies and order |
| [06-operations.md](06-operations.md) | Runbook: deploy, rollback, backups and more (see below) |
| [07-roadmap.md](07-roadmap.md) | What is done, what was deliberately left out, what the next two weeks would bring |
| [08-walkthrough.md](08-walkthrough.md) | The ten minute walkthrough of the system, in order |

- **00-domain.md:** stakeholder map, actors and their jobs, ubiquitous language, roles and
  permissions, domain events, questions for the client.
- **01-requirements.md:** the brief, the writing rules, every requirement with acceptance
  checks, assumptions, exclusions, questions for the client.
- **02-architecture.md:** arc42 sections 1 to 12, C4 diagrams, containers, data flow, quality,
  risks.
- **06-operations.md:** deploy, rollback, backups, secrets, health, what to look at when
  something is wrong.

Conventions:

- arc42 headings for architecture (arc42 is a standard template for architecture documents).
- C4 levels for diagrams (context, container, component).
- ADRs (architecture decision records) in the MADR style.
- Diagrams are kept as Mermaid in the markdown and rendered in the case study site.

The status of each document is in its first lines: draft, reviewed, final.
