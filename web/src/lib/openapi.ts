/** The API's OpenAPI document, fetched from the API at request time (server only). */
import "server-only";
import { apiBaseUrl } from "@/lib/api";

export type Param = { name: string; in: string; required?: boolean; description?: string; schema?: { type?: string; format?: string; enum?: unknown[] } };
export type Operation = {
  method: string;
  path: string;
  summary: string;
  description: string;
  parameters: Param[];
  responses: string[];
  requestBody: string | null;
};
export type Group = { name: string; operations: Operation[] };

type RawOp = {
  summary?: string;
  description?: string;
  parameters?: Param[];
  responses?: Record<string, unknown>;
  requestBody?: { content?: Record<string, { schema?: { $ref?: string } }> };
};
type Schema = { info: { title: string; version: string }; paths: Record<string, Record<string, RawOp>> };

const ORDER = ["weather", "locations", "destination-types", "destinations", "packages", "departures", "travellers", "bookings", "ops"];
const METHODS = ["get", "post", "put", "patch", "delete"];

export async function fetchSchema(): Promise<Schema | null> {
  try {
    const res = await fetch(`${apiBaseUrl()}/api/schema?format=json`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Schema;
  } catch {
    return null;
  }
}

function bodyName(op: RawOp): string | null {
  const ref = op.requestBody?.content?.["application/json"]?.schema?.$ref;
  return ref ? ref.split("/").pop() ?? null : null;
}

export function groupOperations(schema: Schema): Group[] {
  const groups = new Map<string, Operation[]>();
  for (const [path, ops] of Object.entries(schema.paths)) {
    const name = path.replace(/^\/api\/v1\//, "").split("/")[0];
    for (const method of METHODS) {
      const op = ops[method];
      if (!op) continue;
      const list = groups.get(name) ?? [];
      list.push({
        method: method.toUpperCase(),
        path,
        summary: op.summary ?? "",
        description: op.description ?? "",
        parameters: (op.parameters ?? []).filter((p) => p.in !== "header" || p.name.toLowerCase() !== "authorization"),
        responses: Object.keys(op.responses ?? {}),
        requestBody: bodyName(op),
      });
      groups.set(name, list);
    }
  }
  return [...groups.entries()]
    .sort(([a], [b]) => (ORDER.indexOf(a) + 100) % 100 - ((ORDER.indexOf(b) + 100) % 100) || a.localeCompare(b))
    .map(([name, operations]) => ({ name, operations: operations.sort((x, y) => x.path.localeCompare(y.path) || METHODS.indexOf(x.method.toLowerCase()) - METHODS.indexOf(y.method.toLowerCase())) }));
}
