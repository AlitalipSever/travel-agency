"use client";

import { useEffect, useState } from "react";
import { demoFetch, DemoError } from "@/lib/demo-client";
import type { CurrentWeather } from "@/lib/demo-types";
import { spectrum, onSpectrum } from "@/lib/spectrum";
import type { Coordinate } from "@/components/demo/map";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

const SOURCE_HINT: Record<CurrentWeather["source"], string> = {
  live: "fetched from the upstream just now and cached for 10 minutes",
  cached: "answered from the ad hoc cache (younger than 10 minutes), no upstream call",
  stale: "upstream unavailable; a value kept up to 24 hours is served instead",
  sample: "within 100 m of a known location, answered from its stored observations",
};

function parse(v: string, min: number, max: number): number | null {
  const n = Number(v.trim().replace(",", "."));
  return v.trim() !== "" && Number.isFinite(n) && n >= min && n <= max ? n : null;
}

/** Fetches once per coordinate; the parent remounts it per pick (key), so state starts clean. */
function Result({ pick }: { pick: Coordinate }) {
  const [data, setData] = useState<CurrentWeather | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    demoFetch<CurrentWeather>(`weather/current?lat=${pick.lat}&lon=${pick.lon}`)
      .then((r) => !cancelled && setData(r.data))
      .catch((e) => !cancelled && setError(e instanceof DemoError ? `${e.problem.status} ${e.problem.title}: ${e.message}` : String(e)));
    return () => {
      cancelled = true;
    };
  }, [pick]);

  if (error) return <p className="mt-2 text-sm text-destructive">{error}</p>;
  if (!data) return <Skeleton className="mt-3 h-20 w-full" />;
  const t = (data.temp - 5) / 30;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-4 rounded-md border bg-card p-3">
      <span className="rounded px-2 py-1 text-2xl font-medium" style={{ background: spectrum(t), color: onSpectrum(t) }}>
        {data.temp.toFixed(1)}°
      </span>
      <div className="text-sm">
        <p>
          {data.condition} <Badge variant={data.source === "stale" ? "destructive" : "secondary"}>source {data.source}</Badge>
        </p>
        <p className="font-mono text-xs text-muted-foreground">
          {data.lat.toFixed(3)}, {data.lon.toFixed(3)} · {data.timezone} · observed {data.observed_at.slice(11, 16)} UTC · age {data.age_s} s
          {data.humidity != null ? ` · humidity ${data.humidity}%` : ""}
          {data.wind_speed != null ? ` · wind ${data.wind_speed} m/s` : ""}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {SOURCE_HINT[data.source]}
          {data.location_id ? " (a known location)" : ""}. Without an upstream API key the API answers from the nearest recorded fixture.
        </p>
      </div>
    </div>
  );
}

/** Current weather for any coordinate: GET /weather/current?lat=&lon= through the proxy (ad hoc path, ADR 0005). */
export function CurrentWeatherPanel({ pick, onPick }: { pick: Coordinate | null; onPick: (c: Coordinate) => void }) {
  const [error, setError] = useState<string | null>(null);
  const key = pick ? `${pick.lat},${pick.lon}` : "none";

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const la = parse(String(form.get("lat") ?? ""), -90, 90);
    const lo = parse(String(form.get("lon") ?? ""), -180, 180);
    if (la == null || lo == null) {
      setError("lat must be -90 to 90 and lon -180 to 180");
      return;
    }
    setError(null);
    onPick({ lat: la, lon: lo });
  }

  return (
    <div>
      <h3 className="text-lg font-medium">Current weather, any coordinate</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Click anywhere on the map or type a coordinate. Known locations answer from stored samples; any other point goes live, then from the cache for 10 minutes, stale during an outage. Ad hoc calls are rate limited per token, so hammering it shows the 429.
      </p>
      <form key={`form-${key}`} onSubmit={submit} className="mt-3 flex flex-wrap items-end gap-2">
        <label className="label-mono text-muted-foreground">
          lat
          <Input name="lat" defaultValue={pick ? String(pick.lat) : ""} inputMode="decimal" placeholder="-12.046" className="mt-1 w-28 font-mono" />
        </label>
        <label className="label-mono text-muted-foreground">
          lon
          <Input name="lon" defaultValue={pick ? String(pick.lon) : ""} inputMode="decimal" placeholder="-77.043" className="mt-1 w-28 font-mono" />
        </label>
        <Button type="submit" size="sm">
          Fetch
        </Button>
      </form>
      {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
      {pick ? <Result key={`result-${key}`} pick={pick} /> : null}
    </div>
  );
}
