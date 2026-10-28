# 0003 Danger score scale, "at most" semantics, derived in the query

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: P2, P4, P5; A1, A6

## Context

Destinations carry a danger score ("no danger", "medium", "high" in the brief). A package's
score is the greatest of its destinations.

The required endpoint filters "for a given danger score". That can mean equal to, or at most.

## Options

1. Free text or float scores: flexible, but not comparable.
2. Integer 0 to 3 (none, low, medium, high). The filter means "at most"; exact match is a
   flag.
3. Same scale; the filter means exact match only.

## Decision

Option 2.

A client asking for danger 2 wants nothing more dangerous than medium, not exactly medium.
Exact match stays available through `danger_mode=exact`, so the literal reading of the brief
is also served.

The package score is derived in the query (`Max` annotation over the destination join), not
stored. Destinations change, and a stored value would need synchronisation for no measured
gain.

## Consequences

- Adding a destination to a package can change the package's score immediately and
  consistently.
- Inactive destinations still count (P2.5).
- A package with no destinations has a null score and is a draft (P4.2).
- The API shows the score with its label.
- A booking records the package's danger at booking time (P4.5).

If the catalogue grows to a size where the aggregate costs, the next step is a stored,
trigger maintained column. That would be a new ADR.

The same scale is reused for the traveller risk appetite in the suitability extra.
