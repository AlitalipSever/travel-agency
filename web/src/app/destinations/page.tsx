import type { Metadata } from "next";
import { connection } from "next/server";
import { getBrackets, getLocations } from "@/lib/agency-data";
import { DestinationCard, type CityWeather } from "@/components/agency/destination-card";
import { ExploreMap } from "@/components/agency/explore-map";

export const metadata: Metadata = { title: "Destinations" };

export default async function DestinationsPage() {
  await connection();
  let cities: CityWeather[] = [];
  let failed = false;
  try {
    const [locations, brackets] = await Promise.all([getLocations(), getBrackets()]);
    const temps = new Map(brackets.brackets.flatMap((b) => b.locations).map((l) => [l.id, l]));
    cities = locations
      .map((l) => ({ id: l.id, name: l.name, country_code: l.country_code, temp: temps.get(l.id)?.temp ?? null, stale: temps.get(l.id)?.stale ?? false }))
      .sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    failed = true;
  }
  return (
    <div className="mx-auto max-w-6xl px-4 pt-10 pb-20">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Destinations</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        Thirteen capitals in South America. Click a city on the map for its page, or any other point to see the weather there right now.
      </p>
      <div className="mt-8">
        <ExploreMap />
      </div>
      <h2 className="mt-14 text-2xl font-semibold tracking-tight">Our cities</h2>
      <p className="mt-1 text-muted-foreground">The temperature is the latest reading; open a city for the five day forecast.</p>
      {failed ? <p className="mt-8 text-sm text-muted-foreground">The list is not available right now.</p> : null}
      <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {cities.map((c) => <DestinationCard key={c.id} city={c} />)}
      </div>
    </div>
  );
}
