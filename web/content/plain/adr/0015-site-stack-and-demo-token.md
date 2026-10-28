# 0015 Case study site: Next.js App Router with shadcn/ui; the demo token stays server side

Status: proposed
Date: 2026-10-28
Addresses: A17, N1.5, N6.3; work packages W1 to W6

## Context

The case study site has these jobs:

- it renders the documentation;
- it runs a live demo against the API, as the demo partner;
- it shows the operations status.

So far, 02-architecture and 04-api say the following. The browser calls the API directly with the
demo partner's token. CORS (the browser rule that limits which sites may call an API) is
restricted to the site's origin.

A token in a browser bundle is public. Anyone can copy it and call the API from anywhere. And
rotating it means rebuilding the site.

The demo partner's data is isolated and reset nightly (A17), so the damage is bounded. But the
pattern is one we would not accept in a real integration.

## Options

1. The browser calls the API with the token embedded at build time; CORS limits the origin.
   - Simple.
   - The token is public.
   - CORS stops browsers, not scripts.
2. The site's own server calls the API; the browser talks to the site.
   - The token is an environment variable of the `web` container.
   - A route handler forwards an allow-listed subset of the API: reads, and the demo's writes
     (bookings, cancel, travellers).
   - No CORS needed.
3. A short-lived per-visitor token minted by the API.
   - Right for a product.
   - It needs a login flow and a token endpoint that the brief does not ask for (04 §9).

## Decision

Option 2.

- Next.js App Router with shadcn/ui, as the conventions already name.
- Pages render the repository's `docs/` at build time.
- The live demo and the operations page go through `/api/proxy/*` on the site.
- That route adds `Authorization: Token` from `DEMO_PARTNER_TOKEN`. It passes problem responses
  through unchanged.
- The allow list is the demo's surface, nothing more.

## Consequences

- The token never leaves the server. Rotation is a restart of `web`.
- The CORS allowance for the site's origin in 02 §5 and 04 §1 becomes unnecessary and is
  dropped. The API's CORS stays closed.
- Every demo request takes one more hop (inside the cluster, under a millisecond).
- 02 and 04 are updated to point here.
- Revisit if partners need a browser-side integration. That is option 3, not option 1.
