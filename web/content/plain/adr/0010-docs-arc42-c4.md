# 0010 Architecture documentation in arc42 structure with C4 diagrams in Mermaid

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: N1

## Context

The deliverable includes a concise architecture overview. It should highlight data flow,
structure and design choices.

The documentation should also outlive the project. It should be:

- readable in the repository,
- rendered on the case study site,
- maintainable by whoever touches the code next.

## Options

1. One free form README section.
2. arc42 headings with C4 diagrams, written in Mermaid inside markdown. arc42 is a standard
   template for architecture documents. Its headings are goals, constraints, context, strategy,
   building blocks, runtime, deployment, concepts, decisions, quality, risks and glossary. C4
   is a way of drawing a system at zoom levels; here the diagrams cover the context and
   container levels. Decisions are kept as MADR files (a markdown format for decision records).

## Decision

Option 2. The structure forces the questions a reviewer asks. It also keeps the overview
concise, because each section has a job.

Mermaid keeps diagrams in version control. It renders on GitHub and on the site without image
files.

## Consequences

- docs/02-architecture.md follows arc42, with a one-page summary in front (N1).
- C4 views are drawn with Mermaid's plain `flowchart`, not its experimental C4 syntax. The C4
  grammar fails in older renderers (editor previews). So the levels and the box semantics are
  kept, but the notation is not.
- The component level (C4 level 3) is added once code exists.
- Requirements follow the ISO 29148 properties, with acceptance checks (01-requirements §2).
- Every ADR carries an Addresses line that points back to those requirements.
- ADRs live under docs/adr, with the template in 0000-template.md.
- arc42-checklist.md tracks coverage.
