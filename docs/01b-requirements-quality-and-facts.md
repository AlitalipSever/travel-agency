# 01b Quality requirements and facts about the environment

Status: draft, 2026-10-26. Written by the rules in [01-requirements.md](01-requirements.md)
section 2. N items are the brief's non functional expectations; F items are facts that shape
the requirements. They are constraints, not requirements, and are listed so that every
rationale can point at one.

## Non functional requirements

### N1 Architecture overview

- **Statement.** A concise architecture overview aligned with a Python, Django, PostgreSQL, Redis and cloud stack shall describe data flow, structure and the main design choices.
- **Rationale.** The brief's first deliverable.
- **Acceptance.**
  1. arc42 sections 1 to 12 present (arc42-checklist.md), C4 context and container diagrams, every significant choice in an ADR.
- **Satisfied by.** 02-architecture, 02b, adr/.

### N2 Clean data model

- **Statement.** The data model shall be readable in one sitting, with explicit constraints and no duplicated derived values without a stated reason.
- **Rationale.** The brief: "model the data in a clean and professional way".
- **Acceptance.**
  1. ER diagram, constraints and indexes documented; derived values (package danger, remaining seats, end date) computed, not stored, unless an ADR says otherwise.
- **Satisfied by.** 03-data-model; ADR 0002, 0003, 0011.

### N3 Performance, stability, maintainability

- **Statement.** The system shall meet the quality scenarios defined for it and follow the structure rules of the repository.
- **Rationale.** The brief names the three words; scenarios make them measurable.
- **Acceptance.**
  1. Quality scenarios Q1 to Q7 in 02b §10.2 pass (latency unchanged in an upstream outage, zero overbookings, zero failed requests during a deploy, restore under 30 minutes, bounded change effort).
  2. Files under 200 lines, thin views, services per app, tests at the seams (AGENTS.md).
- **Satisfied by.** 02b §10.2; AGENTS.md; CI.

### N4 Extra features

- **Statement.** Extra features and filters that add value for the client shall be proposed and, where the effort is small, implemented.
- **Rationale.** The brief's third deliverable.
- **Acceptance.**
  1. Every proposed extra is tied to a job of an actor in 00-domain §3.
  2. Implemented extras are tested and documented like the required features; proposed ones state what they would take.
- **Satisfied by.** 04-api (extras); 07-roadmap.

### N5 Production ready (our reading of the brief's goal line)

- **Statement.** The system shall run for real, with deployment, rollback, backups, health checks and secret handling in place.
- **Rationale.** The brief's goal line says production ready; we read it as running in production, and mark that as our reading.
- **Acceptance.**
  1. A public URL serves the API and the site over HTTPS.
  2. Deploy and rollback are single commands; a restore drill has been run; secrets are not in git.
- **Satisfied by.** ADR 0006, 0007, 0009; 06-operations.

## Facts about the environment

- **F1** The free tier forecast endpoint returns 40 three hour slots from the next full slot after now, plus one current observation. No daily endpoint, no history, nothing beyond 120 hours. One Call 3.0 offers daily values but needs a paid subscription; the brief says free tier only.
- **F2** The free tier allows 60 calls per minute and about one million per month.
- **F3** The upstream is outside our control: it may be slow, down or rate limiting.
- **F4** Slot timestamps are UTC; the forecast response carries the location's offset. Chile and Paraguay observe daylight saving time; most other South American countries do not.
