import Link from "next/link";
import { Suspense } from "react";
import { connection } from "next/server";
import { ArrowRight } from "lucide-react";
import { AGENCY, HERO_IMAGE } from "@/lib/agency";
import { getBrackets, getPackages, isoToday } from "@/lib/agency-data";
import { Button } from "@/components/ui/button";
import { ScenicImage } from "@/components/agency/scenic-image";
import { HeroSearch } from "@/components/agency/hero-search";
import { TourCard } from "@/components/agency/tour-card";
import { WeatherStrip } from "@/components/agency/weather-strip";

export default function HomePage() {
  return (
    <>
      <section className="relative text-white">
        <ScenicImage src={HERO_IMAGE} alt="The Andes and the Pacific coast" className="absolute inset-0" priority sizes="100vw" />
        <div className="absolute inset-0 bg-gradient-to-t from-spectral-night/80 via-spectral-night/30 to-transparent" />
        <div className="relative mx-auto max-w-6xl px-4 pt-28 pb-10 sm:pt-40">
          <p className="label-mono text-white/80">{AGENCY.tagline}</p>
          <h1 className="mt-3 max-w-2xl text-4xl font-semibold leading-tight tracking-tight sm:text-6xl">
            From the high Andes to the Pacific coast
          </h1>
          <p className="mt-4 max-w-xl text-lg text-white/90">
            Thirteen capitals, small groups, honest advice on the weather and how hard each trip is.
          </p>
          <div className="mt-8">
            <Suspense fallback={<div className="h-24 rounded-xl bg-background/60" />}>
              <SearchWithDates />
            </Suspense>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Our tours</h2>
            <p className="mt-1 text-muted-foreground">Each tour has an adventure level, so you know what to expect.</p>
          </div>
          <Button variant="ghost" nativeButton={false} render={<Link href="/tours" />}>All tours <ArrowRight className="size-4" /></Button>
        </div>
        <Suspense fallback={<div className="mt-6 h-72 rounded-xl border bg-card" />}>
          <FeaturedTours />
        </Suspense>
      </section>

      <section className="bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 py-14">
          <div className="flex items-end justify-between">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Weather today in our cities</h2>
              <p className="mt-1 text-muted-foreground">Live readings, updated every fifteen minutes.</p>
            </div>
            <Button variant="ghost" nativeButton={false} render={<Link href="/destinations" />}>All destinations <ArrowRight className="size-4" /></Button>
          </div>
          <Suspense fallback={<div className="mt-6 h-48 rounded-xl border bg-card" />}>
            <TodayWeather />
          </Suspense>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-8 px-4 py-14 sm:grid-cols-3">
        {[
          ["Small groups", "Never more than twelve travellers. Seats are limited and shown live."],
          ["Clear levels", "Relaxed, Easy, Active or Tough. You pick the level that fits you."],
          ["Weather first", "We watch the weather in every city and tell you what is normal for the season."],
        ].map(([title, text]) => (
          <div key={title}>
            <h3 className="font-semibold">{title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{text}</p>
          </div>
        ))}
      </section>
    </>
  );
}

async function SearchWithDates() {
  await connection();
  return <HeroSearch defaultFrom={isoToday(7)} defaultTo={isoToday(97)} />;
}

async function FeaturedTours() {
  await connection();
  const pkgs = await getPackages().then((all) => all.slice(0, 3)).catch(() => null);
  if (!pkgs) return <p className="mt-6 text-sm text-muted-foreground">Tours are not available right now. Please try again in a minute.</p>;
  return (
    <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {pkgs.map((p) => <TourCard key={p.id} pkg={p} />)}
    </div>
  );
}

async function TodayWeather() {
  await connection();
  const data = await getBrackets().catch(() => null);
  if (!data) return <p className="mt-6 text-sm text-muted-foreground">Weather is not available right now.</p>;
  return <div className="mt-6"><WeatherStrip data={data} /></div>;
}
