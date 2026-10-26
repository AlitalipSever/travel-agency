# 0008 No event streaming (Kafka) in this iteration

Status: proposed
Date: 2026-10-26
Addresses: N4 (deferred); P2, P3, P6 name the events

## Context

Event streaming is a common part of the target stack. The brief's flows are a scheduled
refresh and transactional bookings. An event bus would add a broker, producers, consumers and
delivery semantics to the system.

## Options

1. Add Kafka (or Event Hubs' Kafka endpoint) now, publish weather and booking events.
2. Keep tasks and transactions; design the booking service so an outbox can be added without
   changing callers.

## Decision

Option 2. Nothing in the brief needs asynchronous fan out; adding a broker now would be
complexity without a consumer. The booking service is written behind an interface that a later
outbox publisher can hook into. Named in the roadmap as the first next step.

## Consequences

Simpler operations and tests now. When notifications, analytics or a second service appear,
the outbox pattern is the path and gets its own ADR.
