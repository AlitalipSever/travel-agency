"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { demoFetch } from "@/lib/demo-client";
import type { BracketsResponse, Location } from "@/lib/demo-types";
import { bracketColour } from "@/lib/spectrum";
import { SouthAmericaMap, type Coordinate, type MapPoint } from "@/components/demo/map";
import { PointWeather } from "@/components/agency/point-weather";

/** The map on the destinations page: a city opens its page; any other point shows the weather there now. */
export function ExploreMap() {
  const router = useRouter();
  const [data, setData] = useState<BracketsResponse | null>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [pick, setPick] = useState<Coordinate | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([demoFetch<BracketsResponse>("locations/brackets"), demoFetch<{ results: Location[] }>("locations?page_size=100")])
      .then(([b, l]) => {
        if (cancelled) return;
        setData(b.data);
        setLocations(l.data.results);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const points: MapPoint[] = useMemo(() => {
    if (!data) return [];
    const byId = new Map(locations.map((l) => [l.id, l]));
    const n = data.brackets.length;
    const out: MapPoint[] = [];
    data.brackets.forEach((b, i) =>
      b.locations.forEach((loc) => {
        const l = byId.get(loc.id);
        if (l) out.push({ id: loc.id, name: `${loc.name} ${Math.round(loc.temp)}°`, lat: Number(l.latitude), lon: Number(l.longitude), colour: bracketColour(i, n), stale: loc.stale });
      }),
    );
    data.no_data.forEach((loc) => {
      const l = byId.get(loc.id);
      if (l) out.push({ id: loc.id, name: loc.name, lat: Number(l.latitude), lon: Number(l.longitude), colour: null });
    });
    return out;
  }, [data, locations]);

  return (
    <div className="grid gap-5 lg:grid-cols-[auto_1fr]">
      <div className="rounded-xl border bg-card p-2">
        {points.length === 0 ? (
          <div className="flex h-80 w-64 items-center justify-center text-sm text-muted-foreground lg:h-[420px] lg:w-[340px]">Loading the map…</div>
        ) : (
          <div className="flex justify-center overflow-hidden rounded-lg">
            <SouthAmericaMap points={points} selected={null} onSelect={(id) => router.push(`/destinations/${id}`)} pick={pick} onPick={setPick} className="h-80 w-auto max-w-full lg:h-[420px]" />
          </div>
        )}
        <p className="px-2 pt-2 pb-1 text-xs text-muted-foreground">Colour shows the temperature now: blue is cool, orange is warm. Grey means no reading yet.</p>
      </div>
      <PointWeather pick={pick} cities={locations} />
    </div>
  );
}
