# 0010 Architecture documentation in arc42 structure with C4 diagrams in Mermaid

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: N1

## Context

The deliverable includes a concise architecture overview highlighting data flow, structure and
design choices. The documentation should also survive the project: readable in the repository,
rendered on the case study site, maintainable by whoever touches the code next.

## Options

1. One free form README section.
2. arc42 headings (goals, constraints, context, strategy, building blocks, runtime,
   deployment, concepts, decisions, quality, risks, glossary) with C4 diagrams at context and
   container level, written in Mermaid inside markdown; decisions as MADR files.

## Decision

Option 2. The structure forces the questions a reviewer asks and keeps the overview concise
because each section has a job. Mermaid keeps diagrams in version control and renders on
GitHub and on the site without image files.

## Consequences

docs/02-architecture.md follows arc42 with a one-page summary in front (N1); component level
(C4 level 3) is added once code exists. Requirements follow the ISO 29148 properties with
acceptance checks (01-requirements §2) and every ADR carries an Addresses line back to them.
ADRs under docs/adr with the template in 0000-template.md; arc42-checklist.md tracks coverage.
