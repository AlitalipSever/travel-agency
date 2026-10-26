# travel-agency: operating contract for agents

Standalone repository with its own git and remote; git operations run here. The repository is
meant to be public: it contains the system, its documentation and nothing else. No personal
notes, no references to other projects or workspaces, no names of people or organisations
other than the libraries and services used.

## What this is

A travel agency backend built from a written brief (docs/01-requirements.md). The brief is the
source of truth for scope; assumptions that fill its gaps are listed there and decided in ADRs.

## Rules

- Language: English in code, docs, commits and UI.
- Writing: short sentences, no em dashes, no marketing tone. Documents follow arc42 headings
  where they describe architecture and the ADR template in docs/adr/0000-template.md.
- Every architectural choice gets an ADR before or with the code that implements it. An ADR is
  never edited after acceptance; a new one supersedes it.
- Files stay under 200 lines; split by responsibility (Django apps, Next.js components, chart
  templates). Generated files are exempt.
- Secrets never enter the repo: no API keys, tokens, passwords, kubeconfigs. `.env.example`
  documents the names only.
- Python: Django + Django REST Framework, Celery, pytest, ruff. Views stay thin; domain logic
  lives in a `services` module per app. Migrations are committed.
- TypeScript: Next.js App Router, shadcn/ui, no hand-rolled primitives.
- Containers: multi-stage Dockerfiles, non-root user, arm64 and amd64 images.
- Kubernetes: one Helm chart under `chart/`, environment differences only in values files.
  Resources (requests, limits), readiness and liveness probes on every workload.
- Commits: small, imperative subject, body says why. No AI attribution lines.

## Reading order for a new agent

1. docs/README.md
2. docs/01-requirements.md
3. docs/02-architecture.md
4. docs/adr/ (accepted ones first)
5. The folder you are about to touch
