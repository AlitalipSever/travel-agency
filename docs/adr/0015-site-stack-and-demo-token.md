# 0015 Case study site: Next.js App Router with shadcn/ui; the demo token stays server side

Status: proposed
Date: 2026-10-28
Addresses: A17, N1.5, N6.3; work packages W1 to W6

## Context

The case study site renders the documentation, runs a live demo against the API as the demo
partner and shows the operations status. 02-architecture and 04-api so far say the browser
calls the API directly with the demo partner's token and that CORS is restricted to the site's
origin. A token in a browser bundle is public: anyone can copy it and call the API from
anywhere, and rotating it means rebuilding the site. The demo partner's data is isolated and
reset nightly (A17), so the damage is bounded, but the pattern is one we would not accept in a
real integration.

## Options

1. Browser calls the API with the token embedded at build time; CORS limits the origin. Simple;
   the token is public; CORS stops browsers, not scripts.
2. The site's own server calls the API; the browser talks to the site. The token is an
   environment variable of the `web` container; a route handler forwards an allow-listed subset
   of the API (reads, and the demo's writes: bookings, cancel, travellers). No CORS needed.
3. A short-lived per-visitor token minted by the API. Right for a product; a login flow and a
   token endpoint the brief does not ask for (04 §9).

## Decision

Option 2. Next.js App Router with shadcn/ui as the conventions already name; pages render the
repository's `docs/` at build time; the live demo and the operations page go through
`/api/proxy/*` on the site, which adds `Authorization: Token` from `DEMO_PARTNER_TOKEN` and
passes problem responses through unchanged. The allow list is the demo's surface, nothing more.

## Consequences

The token never leaves the server; rotation is a restart of `web`. The CORS allowance for the
site's origin in 02 §5 and 04 §1 becomes unnecessary and is dropped; the API's CORS stays
closed. One more hop on every demo request (inside the cluster, under a millisecond). 02
and 04 are updated to point here. Revisit if partners need a browser-side integration: that is
option 3, not option 1.
