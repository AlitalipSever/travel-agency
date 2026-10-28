import { connection } from "next/server";
import { fetchSchema, groupOperations, type Operation } from "@/lib/openapi";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const METHOD_TONE: Record<string, string> = {
  GET: "bg-spectral-sky text-white",
  POST: "bg-spectral-deep text-white",
  PATCH: "bg-spectral-apricot text-spectral-night",
  PUT: "bg-spectral-apricot text-spectral-night",
  DELETE: "bg-spectral-ember text-white",
};

function OperationRow({ op }: { op: Operation }) {
  const query = op.parameters.filter((p) => p.in === "query");
  const headers = op.parameters.filter((p) => p.in === "header");
  return (
    <details className="group border-t">
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-2.5 hover:bg-accent/60">
        <span className={`label-mono w-16 rounded px-1.5 py-0.5 text-center ${METHOD_TONE[op.method] ?? "bg-muted"}`}>{op.method}</span>
        <code className="font-mono text-sm">{op.path.replace(/^\/api\/v1/, "")}</code>
        <span className="hidden flex-1 truncate text-sm text-muted-foreground sm:inline">{op.summary}</span>
        <span className="label-mono text-muted-foreground">{op.responses.join(" ")}</span>
      </summary>
      <div className="space-y-3 bg-muted/40 px-4 py-3 text-sm">
        {op.summary ? <p className="sm:hidden">{op.summary}</p> : null}
        {op.description ? <p className="max-w-3xl text-muted-foreground">{op.description}</p> : null}
        {query.length ? (
          <div>
            <p className="label-mono mb-1 text-muted-foreground">Query parameters</p>
            <ul className="grid gap-1 sm:grid-cols-2">
              {query.map((p) => (
                <li key={p.name} className="flex gap-2">
                  <code className="font-mono text-xs">{p.name}{p.required ? "*" : ""}</code>
                  <span className="text-muted-foreground">{p.schema?.enum ? p.schema.enum.join(" | ") : p.schema?.type}{p.description ? ` · ${p.description}` : ""}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {headers.length ? (
          <p className="text-muted-foreground"><span className="label-mono">Headers</span> {headers.map((h) => h.name).join(", ")}</p>
        ) : null}
        {op.requestBody ? <p className="text-muted-foreground"><span className="label-mono">Body</span> {op.requestBody}</p> : null}
      </div>
    </details>
  );
}

/** Reads the API's OpenAPI document at request time and lists it by resource. */
export async function SchemaBrowser() {
  await connection();
  const schema = await fetchSchema();
  if (!schema) {
    return (
      <Alert variant="destructive">
        <AlertTitle>The API did not answer</AlertTitle>
        <AlertDescription>The schema is read from the API at request time; start the stack and reload.</AlertDescription>
      </Alert>
    );
  }
  const groups = groupOperations(schema);
  return (
    <div className="space-y-8">
      <p className="label-mono text-muted-foreground">
        {schema.info.title} {schema.info.version} · OpenAPI 3 · {groups.reduce((n, g) => n + g.operations.length, 0)} operations · token auth
      </p>
      {groups.map((g) => (
        <section key={g.name} id={g.name} className="scroll-mt-20">
          <h2 className="mb-2 font-mono text-sm text-muted-foreground">/{g.name}</h2>
          <div className="overflow-hidden rounded-lg border bg-card [&>details:first-child]:border-t-0">
            {g.operations.map((op) => (
              <OperationRow key={op.method + op.path} op={op} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
