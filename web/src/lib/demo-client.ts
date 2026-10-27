import type { Problem } from "@/lib/demo-types";

/** Browser side calls go to the site's proxy route, which adds the demo token (ADR 0015). */
export class DemoError extends Error {
  constructor(
    public problem: Problem,
    public headers: Headers,
  ) {
    super(problem.detail ?? problem.title);
  }
}

export async function demoFetch<T>(path: string, init: RequestInit = {}): Promise<{ data: T; status: number; headers: Headers }> {
  const res = await fetch(`/api/proxy/${path.replace(/^\//, "")}`, { ...init, cache: "no-store" });
  if (!res.ok) {
    const problem = (await res.json().catch(() => ({ type: "unknown", title: res.statusText, status: res.status }))) as Problem;
    throw new DemoError(problem, res.headers);
  }
  const data = res.status === 204 ? (undefined as T) : ((await res.json()) as T);
  return { data, status: res.status, headers: res.headers };
}

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function daysFromNow(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return isoDate(d);
}
