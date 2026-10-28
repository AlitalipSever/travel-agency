# web

The case study site (work packages W1 to W6): Next.js App Router, TypeScript, Tailwind, shadcn/ui.

```
src/app/              routes: / (overview), /demo, /api, /decisions, /plan, /operations, /walkthrough
src/app/api/proxy/    browser to API bridge; adds the demo partner token server side (ADR 0015)
src/app/healthz/      liveness for the container and the chart
src/components/site/  header, navigation, footer, page header
src/components/spectral/  the visual marks: spectrum bar, isolines
src/components/docs/  markdown, Mermaid (client), section list, document page
src/components/demo/  map (d3-geo + world-atlas), brackets, forecast, bookable search, booking dialog
src/lib/docs.ts       reads docs/ and docs/adr/ at build time (server only)
src/lib/demo-*.ts     response types and the browser side client for the proxy
src/lib/spectrum.ts   the thermal scale as a colour function
src/components/ui/    shadcn/ui components, generated; never edited by hand
src/lib/api.ts        server-side API client (server only)
src/lib/sections.ts   the seven sections
```

Run on the laptop against the compose API:

```
cd web && pnpm install && pnpm dev          # http://localhost:3000
```

Environment (names only; see ../.env.example): `API_URL` (internal, default http://localhost:8000),
`NEXT_PUBLIC_API_URL` (public API origin for the Swagger link), `DEMO_PARTNER_TOKEN` (from
`make demo`; never in git). Visual language: a thermal spectrum read as a scale, cool to warm;
Recursive and IBM Plex Mono, self-hosted (SIL Open Font License).
