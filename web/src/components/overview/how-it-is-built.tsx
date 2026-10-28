const ROWS = [
  ["api", "Django 5.2, Django REST Framework, drf-spectacular, gunicorn", "HTTP API, admin, OpenAPI contract, RFC 7807 errors"],
  ["worker, beat", "Celery on Redis", "Weather refresh on a schedule, spread over the interval; cleanup of old data; refresh when a city is added"],
  ["postgres", "PostgreSQL 16", "The one source of truth: cities, weather samples, tours, departures, bookings"],
  ["redis", "Redis 7", "Task queue, cache for weather at free points, call budget and breaker state"],
  ["web", "Next.js, shadcn/ui", "This site: the agency pages, the documents, the live demo through a server-side proxy, the operations status"],
];

export function HowItIsBuilt() {
  return (
    <section className="border-y bg-card/60">
      <div className="mx-auto max-w-6xl px-4 py-16">
        <p className="label-mono text-muted-foreground">Containers</p>
        <h2 className="mt-2 text-2xl font-medium tracking-tight">Five processes, one compose file, one Helm chart</h2>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          The same images run on a laptop with docker compose and on a Kubernetes node through one Helm chart; only the values files differ. The architecture document follows arc42 with C4 views; decisions have their own page.
        </p>
        <div className="mt-6 overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="label-mono bg-muted text-left text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-normal">Container</th>
                <th className="px-4 py-2 font-normal">Technology</th>
                <th className="px-4 py-2 font-normal">Responsibility</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map(([c, t, r]) => (
                <tr key={c} className="border-t">
                  <td className="px-4 py-2.5 font-mono text-xs">{c}</td>
                  <td className="px-4 py-2.5">{t}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">{r}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
