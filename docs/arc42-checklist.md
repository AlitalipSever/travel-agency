# arc42 checklist

Source: the arc42 template guide, docs.arc42.org (sections 1 to 12, checked 2026-10-26). One
row per official subsection; the status column is updated with every change to
[02-architecture.md](02-architecture.md). Status: done, partial, todo, later (needs code).

| arc42 | Expected (per the guide) | Where | Status |
|---|---|---|---|
| 0 Summary (not an arc42 section; the brief's "concise overview") | One page: what, structure, flows, three decisions, stack | 02 §0 | done |
| 1.1 Requirements overview | Short description of functional requirements, link to the source | 02 §1.1, 01-requirements | done |
| 1.2 Quality goals | 3 to 5 goals, ISO 25010 characteristics, priority order | 02 §1.2 | done |
| 1.3 Stakeholders | Table: role or name, contact, expectations | 02 §1.3, 00-domain §2 | done |
| 2 Constraints | Technical, organisational, conventions; table | 02 §2 | done |
| 3.1 Business context | Context diagram + table of partners with inputs and outputs | 02 §3.1 | done |
| 3.2 Technical context | Channels and protocols, mapping of I/O to channels | 02 §3.2 | done |
| 4 Solution strategy | Fundamental decisions and why | 02 §4 | done |
| 5.1 Building blocks level 1 | Whitebox overview + blackbox table (purpose, interfaces) | 02 §5.1 | partial (diagram yes, table no) |
| 5.2 Building blocks level 2 | Zoom into selected blocks | 02 §5.2 | later |
| 6 Runtime view | Sequence per important scenario | 02 §6 | partial (data flows drawn, sequences after code) |
| 7 Deployment view | Infrastructure, mapping of blocks to nodes | 02 §7 | partial (sizing and pod mapping) |
| 8 Crosscutting concepts | Selected system-wide concepts | 02 §8 | done |
| 9 Architecture decisions | ADRs | adr/ | done (14 accepted 2026-10-27) |
| 10.1 Quality overview | Quality tree or table | 02 §10.1 | todo |
| 10.2 Quality scenarios | Usage and change scenarios with metrics | 02 §10.2 | done |
| 11 Risks and technical debt | Prioritised table with measures | 02 §11 | done |
| 12 Glossary | Term and definition table, lean | 02 §12 (technical), 00-domain §4 (business) | done |

Related documents outside arc42: [00-domain.md](00-domain.md) (stakeholders, actors, jobs to be
done, ubiquitous language, roles), [05-work-packages.md](05-work-packages.md),
[06-operations.md](06-operations.md), [07-roadmap.md](07-roadmap.md).
