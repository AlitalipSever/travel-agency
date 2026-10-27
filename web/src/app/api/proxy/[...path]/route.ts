/**
 * Browser to API bridge for the live demo (ADR 0015). Forwards an allow-listed subset of the
 * API with the demo partner's token added server side; problem responses pass through as is.
 */
import { NextRequest } from "next/server";
import { apiBaseUrl } from "@/lib/api";

const TOKEN = process.env.DEMO_PARTNER_TOKEN ?? "";

const READ_PREFIXES = ["locations", "weather", "packages", "destinations", "destination-types", "departures", "ops", "bookings", "travellers"];
const WRITE_PATTERNS = [/^bookings$/, /^bookings\/[0-9a-f-]+\/cancel$/, /^travellers$/];

function allowed(method: string, path: string): boolean {
  if (method === "GET") return READ_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));
  if (method === "POST") return WRITE_PATTERNS.some((re) => re.test(path));
  return false;
}

async function forward(req: NextRequest, segments: string[]): Promise<Response> {
  const path = segments.join("/");
  if (!allowed(req.method, path)) {
    return Response.json(
      { type: "/problems/forbidden", title: "Not available through the demo", status: 403, detail: `${req.method} ${path} is not part of the demo.` },
      { status: 403, headers: { "Content-Type": "application/problem+json" } },
    );
  }
  const headers = new Headers({ Accept: "application/json" });
  if (TOKEN) headers.set("Authorization", `Token ${TOKEN}`);
  for (const h of ["content-type", "idempotency-key"]) {
    const v = req.headers.get(h);
    if (v) headers.set(h, v);
  }
  const upstream = await fetch(`${apiBaseUrl()}/api/v1/${path}${req.nextUrl.search}`, {
    method: req.method,
    headers,
    body: req.method === "POST" ? await req.text() : undefined,
    cache: "no-store",
  });
  const out = new Headers();
  for (const h of ["content-type", "retry-after", "idempotent-replayed", "x-ratelimit-limit", "x-ratelimit-remaining"]) {
    const v = upstream.headers.get(h);
    if (v) out.set(h, v);
  }
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  return forward(req, (await ctx.params).path);
}

export async function POST(req: NextRequest, ctx: Ctx) {
  return forward(req, (await ctx.params).path);
}
