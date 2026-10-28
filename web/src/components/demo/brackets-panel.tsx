"use client";

import { useEffect, useMemo, useState } from "react";
import { demoFetch, DemoError } from "@/lib/demo-client";
import type { BracketsResponse, Location } from "@/lib/demo-types";
import { bracketColour, onSpectrum } from "@/lib/spectrum";
import { SouthAmericaMap, type Coordinate, type MapPoint } from "@/components/demo/map";
import { ForecastPanel } from "@/components/demo/forecast-panel";
import { CurrentWeatherPanel } from "@/components/demo/current-weather-panel";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

type Mode = "fixed" | "quantile";

export function BracketsPanel() {
  const [mode, setMode] = useState<Mode>("fixed");
  const [buckets, setBuckets] = useState(4);
  const [data, setData] = useState<BracketsResponse | null>(null);
  const [locations, setLocations] = useState<Record<string, Location>>({});
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [pick, setPick] = useState<Coordinate | null>(null);

  const query = mode === "quantile" ? `?mode=quantile&buckets=${buckets}` : "";

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      demoFetch<BracketsResponse>(`locations/brackets${query}`),
      demoFetch<{ results: Location[] }>("locations?page_size=100"),
    ])
      .then(([b, l]) => {
        if (cancelled) return;
        setData(b.data);
        setLocations(Object.fromEntries(l.data.results.map((x) => [x.id, x])));
        setError(null);
      })
      .catch((e) => !cancelled && setError(e instanceof DemoError ? e.message : String(e)));
    return () => {
      cancelled = true;
    };
  }, [query]);

  const n = data?.brackets.length ?? 0;
  const points: MapPoint[] = useMemo(() => {
    if (!data) return [];
    const out: MapPoint[] = [];
    data.brackets.forEach((b, i) =>
      b.locations.forEach((loc) => {
        const l = locations[loc.id];
        if (l) out.push({ id: loc.id, name: loc.name, lat: +l.latitude, lon: +l.longitude, colour: bracketColour(i, n), stale: loc.stale });
      }),
    );
    data.no_data.forEach((loc) => {
      const l = locations[loc.id];
      if (l) out.push({ id: loc.id, name: loc.name, lat: +l.latitude, lon: +l.longitude, colour: null });
    });
    return out;
  }, [data, locations, n]);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <div>
        <SouthAmericaMap points={points} selected={selected} onSelect={setSelected} pick={pick} onPick={setPick} />
        <p className="label-mono mt-2 text-muted-foreground">Map: Natural Earth via world-atlas, public domain. Dashed ring: stale or no reading. Click a point for its forecast, anywhere else for the current weather there.</p>
      </div>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <ToggleGroup value={[mode]} onValueChange={(v) => v[0] && setMode(v[0] as Mode)} variant="outline" size="sm">
            <ToggleGroupItem value="fixed">Fixed edges</ToggleGroupItem>
            <ToggleGroupItem value="quantile">Quantile</ToggleGroupItem>
          </ToggleGroup>
          {mode === "quantile" ? (
            <ToggleGroup value={[String(buckets)]} onValueChange={(v) => v[0] && setBuckets(+v[0])} variant="outline" size="sm">
              {[3, 4, 5, 6].map((k) => (
                <ToggleGroupItem key={k} value={String(k)}>{k}</ToggleGroupItem>
              ))}
            </ToggleGroup>
          ) : null}
          {data ? (
            <span className="label-mono text-muted-foreground">
              edges {data.edges.map((e) => e.toFixed(1)).join(" · ")} · refreshed {data.refreshed_at ? new Date(data.refreshed_at).toUTCString().slice(17, 22) + " UTC" : "never"}
            </span>
          ) : null}
        </div>
        {error ? (
          <Alert variant="destructive"><AlertTitle>Brackets unavailable</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>
        ) : null}
        {!data && !error ? <Skeleton className="h-48 w-full" /> : null}
        {data ? (
          <ol className="divide-y rounded-lg border bg-card">
            {data.brackets.map((b, i) => {
              const t = n <= 1 ? 0.5 : i / (n - 1);
              return (
                <li key={b.label} className="flex items-start gap-3 px-3 py-2">
                  <span className="label-mono mt-0.5 w-24 shrink-0 rounded px-1.5 py-0.5 text-center" style={{ background: bracketColour(i, n), color: onSpectrum(t) }}>
                    {b.label}
                  </span>
                  <span className="flex flex-1 flex-wrap gap-x-3 gap-y-1 text-sm">
                    {b.locations.length === 0 ? <span className="text-muted-foreground">empty</span> : null}
                    {b.locations.map((loc) => (
                      <button key={loc.id} type="button" onClick={() => setSelected(loc.id)} className={`rounded px-1 hover:bg-accent ${selected === loc.id ? "bg-accent font-medium" : ""}`}>
                        {loc.name} <span className="font-mono text-xs text-muted-foreground">{loc.temp.toFixed(1)}°{loc.stale ? " stale" : ""}</span>
                      </button>
                    ))}
                  </span>
                  <span className="label-mono text-muted-foreground">{b.count}</span>
                </li>
              );
            })}
            {data.no_data.length ? (
              <li className="flex items-start gap-3 px-3 py-2">
                <span className="label-mono mt-0.5 w-24 shrink-0 rounded border px-1.5 py-0.5 text-center text-muted-foreground">no_data</span>
                <span className="flex-1 text-sm text-muted-foreground">{data.no_data.map((l) => l.name).join(", ")}</span>
                <span className="label-mono text-muted-foreground">{data.no_data.length}</span>
              </li>
            ) : null}
          </ol>
        ) : null}
        <ForecastPanel key={selected ?? "none"} locationId={selected} name={selected ? locations[selected]?.name : undefined} />
        <CurrentWeatherPanel pick={pick} onPick={setPick} />
      </div>
    </div>
  );
}
