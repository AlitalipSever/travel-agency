import { redirect } from "next/navigation";
import { connection } from "next/server";

/** Swagger UI lives on the API; the public API origin may differ from the internal one. */
export async function GET() {
  // Opt out of build-time prerendering (cacheComponents is on): the origin is read per request.
  await connection();
  // API_PUBLIC_URL is read at runtime (cluster ConfigMap); NEXT_PUBLIC_* values are inlined at
  // build time and only fit docker compose, where the API is on localhost:8000 anyway.
  const base = process.env.API_PUBLIC_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  redirect(`${base}/api/docs`);
}
