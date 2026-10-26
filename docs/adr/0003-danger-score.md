# 0003 Danger score scale, "at most" semantics, derived in the query

Status: proposed
Date: 2026-10-26
Addresses: P2, P4, P5; A1, A6

## Context

Destinations carry a danger score ("no danger", "medium", "high" in the brief). A package's
score is the greatest of its destinations. The required endpoint filters "for a given danger
score", which can mean equal to or at most.

## Options

1. Free text or float scores: flexible, not comparable.
2. Integer 0 to 3 (none, low, medium, high); filter means "at most"; exact match as a flag.
3. Same scale; filter means exact match only.

## Decision

Option 2. A client asking for danger 2 wants nothing more dangerous than medium, not exactly
medium; exact match stays available through `danger_mode=exact` so the literal reading of the
brief is also served. The package score is derived in the query (`Max` annotation over the
destination join), not stored: destinations change, and a stored value would need
synchronisation for no measured gain.

## Consequences

Adding a destination to a package can change the package's score immediately and
consistently. If the catalogue grows to a size where the aggregate costs, a stored, trigger
maintained column is the next step and would be a new ADR. The same scale is reused for the
traveller risk appetite in the suitability extra.
