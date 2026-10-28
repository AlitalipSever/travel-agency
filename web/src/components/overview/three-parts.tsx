import { CloudSun, MapPinned, Route } from "lucide-react";

const PARTS = [
  {
    icon: CloudSun,
    title: "Weather in, on a schedule",
    text: "A background job saves the current weather and the five day forecast for every known city into PostgreSQL. A request for a known city never calls the weather service. Other points go through a cache, a call budget and a circuit breaker; old data is marked as old before we answer 503.",
    tags: ["W1 to W4", "ADR 0005", "ADR 0012", "ADR 0013"],
  },
  {
    icon: MapPinned,
    title: "Locations by temperature bracket",
    text: "Thirteen South American capitals with their time zones, grouped by temperature. The group edges come from a settings table; quantile mode takes them from today's readings so no group is empty. Cities without a reading are listed, not hidden.",
    tags: ["L1 to L4", "ADR 0004"],
  },
  {
    icon: Route,
    title: "Packages, departures, the bookable search",
    text: "A tour's danger score is the highest score of its stops, computed in the query, never stored. Seats belong to a departure date; free seats are counted from confirmed bookings under a row lock. The search returns tours with a planned date in the range and seats left.",
    tags: ["P1 to P6", "ADR 0002", "ADR 0003", "ADR 0011"],
  },
];

export function ThreeParts() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16">
      <p className="label-mono text-muted-foreground">The brief in three parts</p>
      <div className="mt-6 grid gap-6 md:grid-cols-3">
        {PARTS.map((p) => (
          <article key={p.title} className="rounded-lg border bg-card p-5">
            <p.icon className="size-5 text-spectral-sky" aria-hidden="true" />
            <h2 className="mt-3 text-lg font-medium tracking-tight">{p.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.text}</p>
            <div className="mt-4 flex flex-wrap gap-1.5">
              {p.tags.map((t) => (
                <span key={t} className="label-mono rounded border px-1.5 py-0.5 text-muted-foreground">{t}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
