# 0008 No event streaming (Kafka) in this iteration

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: N4 (deferred); P2, P3, P6 name the events

## Context

Event streaming is a common part of the target stack.

The brief's flows are a scheduled refresh and transactional bookings. An event bus would add a
broker, producers, consumers and delivery semantics to the system.

## Options

1. Add Kafka (or Event Hubs' Kafka endpoint) now, and publish weather and booking events.
2. Keep tasks and transactions. Design the booking service so an outbox can be added without
   changing callers.

## Decision

Option 2. Nothing in the brief needs asynchronous fan out. Adding a broker now would be
complexity without a consumer.

The booking service is written behind an interface that a later outbox publisher can hook
into. The events are already named in 00-domain §6 and in P2, P3 and P6.

This is named in the roadmap as the first next step.

## Consequences

Simpler operations and tests now.

When notifications, analytics or a second service appear, the outbox pattern is the path. It
gets its own ADR. (The outbox pattern writes events to a table in the same transaction as the
data, and a separate publisher sends them on.)
