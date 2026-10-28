"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MapPin } from "lucide-react";
import { demoFetch, DemoError } from "@/lib/demo-client";
import type { CurrentWeather, Location } from "@/lib/demo-types";
import type { Coordinate } from "@/components/demo/map";
import { Skeleton } from "@/components/ui/skeleton";

const SOURCE_WORDS: Record<CurrentWeather["source"], string> = {
  live: "live reading",
  cached: "from the last few minutes",
  stale: "older reading, the weather service did not answer",
  sample: "from our records for this city",
};

function distanceKm(a: Coordinate, b: Coordinate): number {
  const r = Math.PI / 180;
  const dLat = (b.lat - a.lat) * r;
  const dLon = (b.lon - a.lon) * r;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(h));
}

/** Weather for a free point on the map, in customer words; the parent remounts it per pick (key). */
export function PointWeather({ pick, cities }: { pick: Coordinate | null; cities: Location[] }) {
  return (
    <div className="rounded-xl border bg-card p-5">
      <h3 className="font-semibold">Weather at the point you picked</h3>
      {pick ? <Reading key={`${pick.lat},${pick.lon}`} pick={pick} cities={cities} /> : (
        <p className="mt-2 text-sm text-muted-foreground">Click anywhere on the map to see the weather there right now. Click a city to open its page.</p>
      )}
    </div>
  );
}

function Reading({ pick, cities }: { pick: Coordinate; cities: Location[] }) {
  const [data, setData] = useState<CurrentWeather | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    demoFetch<CurrentWeather>(`weather/current?lat=${pick.lat.toFixed(4)}&lon=${pick.lon.toFixed(4)}`)
      .then((r) => !cancelled && setData(r.data))
      .catch((e) => !cancelled && setFailed(e instanceof DemoError || true));
    return () => {
      cancelled = true;
    };
  }, [pick]);

  const nearest = cities
    .map((c) => ({ c, km: distanceKm(pick, { lat: Number(c.latitude), lon: Number(c.longitude) }) }))
    .sort((a, b) => a.km - b.km)[0];

  return (
    <div className="mt-3 space-y-3">
      <p className="text-xs text-muted-foreground">{pick.lat.toFixed(2)}, {pick.lon.toFixed(2)}</p>
      {failed ? (
        <p className="text-sm text-muted-foreground">No weather for this point right now. Please try again in a minute.</p>
      ) : !data ? (
        <Skeleton className="h-16 w-full" />
      ) : (
        <div>
          <p className="text-3xl font-semibold">{Math.round(data.temp)}° <span className="text-base font-normal text-muted-foreground">{data.condition}</span></p>
          <p className="mt-1 text-sm text-muted-foreground">
            {data.humidity != null ? `Humidity ${data.humidity}%` : null}
            {data.wind_speed != null ? ` · wind ${data.wind_speed} m/s` : null}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{SOURCE_WORDS[data.source]}, {data.observed_at.slice(11, 16)} UTC</p>
        </div>
      )}
      {nearest ? (
        <p className="flex items-center gap-1 border-t pt-3 text-sm">
          <MapPin className="size-4 text-muted-foreground" />
          Nearest of our cities: <Link href={`/destinations/${nearest.c.id}`} className="font-medium hover:underline">{nearest.c.name}</Link>
          <span className="text-muted-foreground">, {Math.round(nearest.km)} km</span>
        </p>
      ) : null}
    </div>
  );
}
