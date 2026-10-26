# 08 Walkthrough

Status: draft, 2026-10-26. Ten minutes, in this order. The site's walkthrough page follows the
same sections.

1. **It runs.** Open the live site. Brackets page shows today's temperatures of the South
   American capitals. Click one: five day forecast. 60 seconds.
2. **The brief, decomposed.** Three parts: weather proxy, locations and brackets, the product
   model. One slide with the ten assumptions that fill the brief's gaps. 60 seconds.
3. **Architecture.** Context and container diagrams. Data flow for one weather request (cache
   hit, miss, stale) and for one bookable query. 2 minutes.
4. **Three decisions and their trade-offs.** Departure as the sellable unit; danger derived in
   the query; cache and scheduled refresh instead of calling upstream per request. Each with
   the option not taken. 2 minutes.
5. **Production.** Terraform, Helm, CI/CD, operator managed PostgreSQL with backups, HTTPS,
   probes and resources. The operations page with live numbers. Why k3s on Hetzner and how the
   same chart goes to AKS. 2 minutes.
6. **Extras.** Booking with a row lock and idempotency; suitability by customer risk appetite;
   weather aware filter. Demo one booking that sells out. 90 seconds.
7. **What I left out and what comes next.** The roadmap page. 30 seconds.
8. Questions.
