import type { Metadata } from "next";
import { connection } from "next/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { cityImage } from "@/lib/agency";
import { citiesOf, getLocations, getPackages } from "@/lib/agency-data";
import { ScenicImage } from "@/components/agency/scenic-image";
import { TourCard } from "@/components/agency/tour-card";
import { ForecastPanel } from "@/components/demo/forecast-panel";

export async function generateMetadata({ params }: PageProps<"/destinations/[id]">): Promise<Metadata> {
  const { id } = await params;
  const city = (await getLocations().catch(() => [])).find((l) => l.id === id);
  return { title: city ? city.name : "Destination" };
}

export default async function DestinationPage({ params }: PageProps<"/destinations/[id]">) {
  await connection();
  const { id } = await params;
  const [locations, packages] = await Promise.all([getLocations(), getPackages().catch(() => [])]);
  const city = locations.find((l) => l.id === id);
  if (!city) notFound();
  const tours = packages.filter((p) => citiesOf(p).includes(city.name));

  return (
    <>
      <section className="relative text-white">
        <ScenicImage src={cityImage(city.name)} alt={city.name} className="absolute inset-0" priority sizes="100vw" />
        <div className="absolute inset-0 bg-gradient-to-t from-spectral-night/80 to-transparent" />
        <div className="relative mx-auto max-w-6xl px-4 pt-32 pb-10 sm:pt-48">
          <Link href="/destinations" className="inline-flex items-center gap-1 text-sm text-white/80 hover:text-white"><ArrowLeft className="size-4" /> All destinations</Link>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{city.name}</h1>
          <p className="mt-1 text-white/85">{city.country_code} · time zone {city.timezone}</p>
        </div>
      </section>
      <div className="mx-auto max-w-6xl space-y-12 px-4 py-12">
        <section>
          <h2 className="text-xl font-semibold tracking-tight">Weather now and the next five days</h2>
          <p className="mt-1 mb-4 text-sm text-muted-foreground">Day averages from the forecast; the first day can be partial.</p>
          <ForecastPanel locationId={city.id} name={city.name} />
        </section>
        <section>
          <h2 className="text-xl font-semibold tracking-tight">Tours that visit {city.name}</h2>
          {tours.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">No tour stops here yet. <Link href="/tours" className="underline">See all tours</Link>.</p>
          ) : (
            <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{tours.map((p) => <TourCard key={p.id} pkg={p} />)}</div>
          )}
        </section>
      </div>
    </>
  );
}
