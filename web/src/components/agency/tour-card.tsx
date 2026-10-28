import Link from "next/link";
import { CalendarDays, Clock } from "lucide-react";
import { citiesOf, type TourPackage } from "@/lib/agency-data";
import { longDate, money, tourImage } from "@/lib/agency";
import { ScenicImage } from "@/components/agency/scenic-image";
import { LevelBadge } from "@/components/agency/level-badge";

export function TourCard({ pkg, note }: { pkg: TourPackage; note?: string }) {
  const cities = citiesOf(pkg);
  const next = pkg.departures_summary?.next ?? null;
  return (
    <Link href={`/tours/${pkg.id}`} className="group flex flex-col overflow-hidden rounded-xl border bg-card transition-shadow hover:shadow-md">
      <ScenicImage src={tourImage(pkg.name, cities[0])} alt={pkg.name} className="aspect-[16/10]" />
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold leading-tight group-hover:underline">{pkg.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{cities.join(" · ")}</p>
          </div>
          <LevelBadge score={pkg.danger} />
        </div>
        <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1"><Clock className="size-3.5" /> {pkg.duration_days} days</span>
          {next ? (
            <span className="inline-flex items-center gap-1">
              <CalendarDays className="size-3.5" /> Next: {longDate(next.starts_on)}
              {next.remaining_seats === 0 ? " (full)" : ` · ${next.remaining_seats} seats`}
            </span>
          ) : null}
          {note ? <span>{note}</span> : null}
        </div>
        <p className="text-base"><span className="font-semibold">{money(pkg.price, pkg.currency)}</span> <span className="text-sm text-muted-foreground">per person</span></p>
      </div>
    </Link>
  );
}
