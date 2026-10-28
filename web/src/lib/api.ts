/**
 * Server-side client for the backend API. The demo partner's token lives only here, read from
 * the environment; browsers reach the API through the route handler under /api/proxy, which
 * calls this module (ADR 0015). Never import this file from a client component.
 */
import "server-only";

const API_URL = process.env.API_URL ?? "http://localhost:8000";
const TOKEN = process.env.DEMO_PARTNER_TOKEN ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    public problem: Record<string, unknown>,
  ) {
    super(typeof problem.detail === "string" ? problem.detail : `API error ${status}`);
  }
}

export function apiBaseUrl(): string {
  return API_URL;
}

/** Fetch a path under /api/v1 with the demo token; throws ApiError on a problem response. */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (TOKEN) headers.set("Authorization", `Token ${TOKEN}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const res = await fetch(`${API_URL}/api/v1${path}`, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    const problem = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    throw new ApiError(res.status, problem);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
