import type { Metadata } from "next";
import { connection } from "next/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Clock, MapPin } from "lucide-react";
import { LEVELS, levelLabel, money, tourImage } from "@/lib/agency";
import { citiesOf, getDepartures, getPackage } from "@/lib/agency-data";
import { ScenicImage } from "@/components/agency/scenic-image";
import { LevelBadge } from "@/components/agency/level-badge";
import { TourBooking } from "@/components/agency/tour-booking";

export async function generateMetadata({ params }: PageProps<"/tours/[id]">): Promise<Metadata> {
  const { id } = await params;
  const pkg = await getPackage(id).catch(() => null);
  return { title: pkg ? pkg.name : "Tour" };
}

export default async function TourPage({ params }: PageProps<"/tours/[id]">) {
  await connection();
  const { id } = await params;
  const pkg = await getPackage(id);
  if (!pkg) notFound();
  const departures = await getDepartures(pkg.id).catch(() => []);
  const cities = citiesOf(pkg);
  const level = LEVELS[Math.min(3, pkg.danger)];

  return (
    <>
      <section className="relative text-white">
        <ScenicImage src={tourImage(pkg.name, cities[0])} alt={pkg.name} className="absolute inset-0" priority sizes="100vw" />
        <div className="absolute inset-0 bg-gradient-to-t from-spectral-night/85 to-transparent" />
        <div className="relative mx-auto max-w-6xl px-4 pt-32 pb-10 sm:pt-48">
          <Link href="/tours" className="inline-flex items-center gap-1 text-sm text-white/80 hover:text-white"><ArrowLeft className="size-4" /> All tours</Link>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl">{pkg.name}</h1>
          <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-white/90">
            <span className="inline-flex items-center gap-1"><MapPin className="size-4" /> {cities.join(" · ")}</span>
            <span className="inline-flex items-center gap-1"><Clock className="size-4" /> {pkg.duration_days} days</span>
            <LevelBadge score={pkg.danger} />
          </p>
        </div>
      </section>

      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-10">
          <section>
            <h2 className="text-xl font-semibold tracking-tight">The route</h2>
            <ol className="mt-4 space-y-3">
              {pkg.destinations.map((d) => (
                <li key={d.id} className="flex gap-3 rounded-xl border bg-card p-4">
                  <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-spectral-sky text-sm font-medium text-white">{d.position}</span>
                  <div>
                    <div className="font-medium">{d.name}</div>
                    <div className="text-sm text-muted-foreground">
                      <Link href={`/destinations/${d.location.id}`} className="hover:underline">{d.location.name}</Link> · {d.type} · {levelLabel(d.danger)}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </section>
          <section>
            <h2 className="text-xl font-semibold tracking-tight">Adventure level: {level.label}</h2>
            <p className="mt-2 text-muted-foreground">{level.hint}. The level of a tour is the level of its hardest stop.</p>
            {pkg.description ? <p className="mt-3 text-muted-foreground">{pkg.description}</p> : null}
          </section>
        </div>
        <aside className="h-fit space-y-4 lg:sticky lg:top-24">
          <div className="rounded-xl border bg-card p-5">
            <p className="text-2xl font-semibold">{money(pkg.price, pkg.currency)} <span className="text-sm font-normal text-muted-foreground">per person</span></p>
            <p className="mt-1 text-sm text-muted-foreground">{pkg.duration_days} days · small group, at most twelve seats per date.</p>
          </div>
          <div>
            <h2 className="mb-3 font-semibold">Dates</h2>
            <TourBooking pkg={{ ...pkg, departures: [] }} departures={departures} />
            <p className="mt-3 text-xs text-muted-foreground">Demo site: a booking here is a test booking under the demo partner and is reset every night.</p>
          </div>
        </aside>
      </div>
    </>
  );
}
