# 08 Walkthrough

Status: reviewed against 00 to 07, 2026-10-27. Ten minutes, in this order; the site's
walkthrough page follows the same sections and pulls its content from the other pages.

1. **It runs.** Open the live site. The brackets page shows today's temperatures of the
   thirteen capitals grouped by bracket, with any `no_data` rows visible; click one for the
   forecast: `today` separate from the five days, `partial` and sample counts shown. 60 s.
2. **Who it is for, and what I asked first.** The stakeholder onion, the four roles and the
   demo partner, the traveller as a record not a user, and the questions I would put to the
   client with the assumption I worked with (00-domain §7). Then the brief in three parts and
   the seventeen assumptions (01 §3). 90 s.
3. **Architecture.** The one-page summary (02 §0): context and container views, the two data
   flows (weather in on a schedule into PostgreSQL; the bookable search out of one query), and
   R4: two sales, one seat, one 409. 2 min.
4. **Three decisions and their trade-offs.** Departure as the sellable unit with a row lock
   (ADR 0002); danger derived in the query, never stored (ADR 0003); known locations never
   fetched on the request path, budget split and breaker (ADR 0005, 0012). Each with the
   option not taken and the signal that would change it (07 §4). 2 min.
5. **Honesty in the data.** `source`, `stale`, `partial`, sample counts, `observed_at`; 503
   only when nothing is stored; the risks table (02 §11) and what is deliberately left out
   (07 §2). 60 s.
6. **Production, local first.** The same Helm chart on kind and on the server: migrate job,
   rolling update, probes, operator-managed PostgreSQL with backups and a rehearsed restore,
   trigger-based history, HTTPS. The operations page with live numbers (`/ops/status`). Why
   k3s on Hetzner for about 10 EUR a month and how the same chart goes to AKS. 90 s.
7. **Extras from the actors' jobs.** Booking with capacity, concurrency and idempotency (demo
   one departure selling out and the 409); suitability by traveller risk appetite; the weather
   aware filter with its "conditions now" note. 60 s.
8. **What comes next.** The roadmap page: next two weeks and how the team would grow. 30 s.
9. Questions.
