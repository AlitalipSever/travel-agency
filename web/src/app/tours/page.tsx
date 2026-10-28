import type { Metadata } from "next";
import { Suspense } from "react";
import { connection } from "next/server";
import { LEVELS, levelLabel, longDate } from "@/lib/agency";
import { getPackages, isoToday, searchBookable, type TourPackage } from "@/lib/agency-data";
import { HeroSearch } from "@/components/agency/hero-search";
import { TourCard } from "@/components/agency/tour-card";

export const metadata: Metadata = { title: "Tours" };

export default async function ToursPage({ searchParams }: PageProps<"/tours">) {
  const sp = await searchParams;
  const from = typeof sp.from === "string" ? sp.from : "";
  const to = typeof sp.to === "string" ? sp.to : "";
  const level = typeof sp.level === "string" ? Math.min(3, Math.max(0, Number(sp.level) || 0)) : 3;
  const searching = Boolean(from && to);

  return (
    <div className="mx-auto max-w-6xl px-4 pt-10 pb-20">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Tours</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        Pick your dates and the highest adventure level you want. We show only tours with free seats in that time.
      </p>
      <div className="mt-6">
        <Suspense fallback={<div className="h-24 rounded-xl border bg-card" />}>
          <SearchForm from={from} to={to} level={searching ? level : 2} />
        </Suspense>
      </div>
      <Suspense fallback={<div className="mt-8 h-64 rounded-xl border bg-card" />}>
        {searching ? <SearchResults from={from} to={to} level={level} /> : <AllTours />}
      </Suspense>
    </div>
  );
}

async function SearchForm({ from, to, level }: { from: string; to: string; level: number }) {
  await connection();
  return <HeroSearch defaultFrom={from || isoToday(7)} defaultTo={to || isoToday(97)} defaultLevel={level} />;
}

async function AllTours() {
  await connection();
  const pkgs = await getPackages().catch(() => null);
  if (!pkgs) return <p className="mt-8 text-sm text-muted-foreground">Tours are not available right now.</p>;
  return <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{pkgs.map((p) => <TourCard key={p.id} pkg={p} />)}</div>;
}

type Row = { pkg: TourPackage; note: string | undefined };

async function loadResults(from: string, to: string, level: number): Promise<Row[] | null> {
  try {
    const [res, all] = await Promise.all([searchBookable({ from, to, danger: level }), getPackages()]);
    const byId = new Map(all.map((p) => [p.id, p]));
    return res.results.flatMap((r) => {
      const pkg = byId.get(r.id);
      if (!pkg) return [];
      const first = r.departures[0];
      const note = first ? `${r.departures.length} date${r.departures.length === 1 ? "" : "s"}, first ${longDate(first.starts_on)}` : undefined;
      return [{ pkg, note }];
    });
  } catch {
    return null;
  }
}

async function SearchResults({ from, to, level }: { from: string; to: string; level: number }) {
  await connection();
  const rows = await loadResults(from, to, level);
  if (!rows) return <p className="mt-8 text-sm text-muted-foreground">Please check the dates: the start must be before the end and within one year.</p>;
  return (
    <>
      <p className="mt-8 text-sm text-muted-foreground">
        {rows.length === 0
          ? "No tour fits these dates and level. Try a wider date range or a higher level."
          : `${rows.length} tour${rows.length === 1 ? "" : "s"} between ${longDate(from)} and ${longDate(to)}, level up to ${levelLabel(level)}.`}
      </p>
      <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{rows.map(({ pkg, note }) => <TourCard key={pkg.id} pkg={pkg} note={note} />)}</div>
      <p className="mt-8 text-xs text-muted-foreground">Levels: {LEVELS.map((l) => `${l.label} = ${l.hint.toLowerCase()}`).join("; ")}.</p>
    </>
  );
}
