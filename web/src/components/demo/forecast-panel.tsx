"use client";

import { useEffect, useState } from "react";
import { demoFetch, DemoError } from "@/lib/demo-client";
import type { DaySummary, ForecastResponse } from "@/lib/demo-types";
import { spectrum, onSpectrum } from "@/lib/spectrum";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

function tone(temp: number | null): string {
  if (temp == null) return "transparent";
  return spectrum((temp - 5) / 30);
}

function Day({ d, label }: { d: DaySummary; label: string }) {
  const t = d.temp_avg == null ? 0.5 : (d.temp_avg - 5) / 30;
  return (
    <div className="min-w-0 rounded-md border bg-card p-2.5">
      <p className="label-mono text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm">{d.date.slice(5)}</p>
      <p className="mt-2 inline-block rounded px-1.5 py-0.5 text-lg font-medium" style={{ background: tone(d.temp_avg), color: onSpectrum(t) }}>
        {d.temp_avg == null ? "–" : `${d.temp_avg.toFixed(1)}°`}
      </p>
      <p className="font-mono text-[11px] text-muted-foreground">
        {d.temp_min == null ? "–" : d.temp_min.toFixed(1)} / {d.temp_max == null ? "–" : d.temp_max.toFixed(1)}
      </p>
      <p className="mt-1 text-xs">{d.condition}</p>
      <p className="label-mono mt-1 text-muted-foreground">
        {d.observed_samples}o {d.forecast_samples}f{d.partial ? " · partial" : ""}
      </p>
    </div>
  );
}

export function ForecastPanel({ locationId, name }: { locationId: string | null; name?: string }) {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!locationId) return;
    let cancelled = false; // the parent remounts this panel per location (key), so state starts clean
    demoFetch<ForecastResponse>(`locations/${locationId}/weather/forecast`)
      .then((r) => !cancelled && setData(r.data))
      .catch((e) => !cancelled && setError(e instanceof DemoError ? `${e.problem.status} ${e.message}` : String(e)));
    return () => {
      cancelled = true;
    };
  }, [locationId]);

  if (!locationId) return <p className="text-sm text-muted-foreground">Select a location on the map or in the list for its forecast: today, then five days, each with its sample counts and whether it is partial.</p>;
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-lg font-medium">{name ?? "Forecast"}</h3>
        {data ? (
          <>
            <Badge variant={data.source === "stale" ? "destructive" : "secondary"}>source {data.source}</Badge>
            <span className="label-mono text-muted-foreground">{data.timezone} · as of {data.as_of.slice(11, 16)} UTC</span>
          </>
        ) : null}
      </div>
      {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
      {!data && !error ? <Skeleton className="mt-3 h-32 w-full" /> : null}
      {data ? (
        <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
          {data.today ? <Day d={data.today} label="today" /> : <div className="rounded-md border border-dashed p-2.5 text-xs text-muted-foreground">today: no data</div>}
          {data.days.map((d, i) => (
            <Day key={d.date} d={d} label={`day ${i + 1}`} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
