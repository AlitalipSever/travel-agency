"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { BookableDeparture, BookablePackage } from "@/lib/demo-types";
import { longDate } from "@/lib/agency";
import { Button } from "@/components/ui/button";
import { BookingDialog } from "@/components/demo/booking-dialog";

/** Departure list with a Book button each; the dialog is the same one the live demo uses. */
export function TourBooking({ pkg, departures }: { pkg: BookablePackage; departures: BookableDeparture[] }) {
  const router = useRouter();
  const [target, setTarget] = useState<{ pkg: BookablePackage; dep: BookableDeparture } | null>(null);

  if (departures.length === 0) return <p className="text-sm text-muted-foreground">No dates planned right now. Please check again soon.</p>;

  return (
    <>
      <ul className="divide-y rounded-xl border bg-card">
        {departures.map((dep) => {
          const full = dep.remaining_seats <= 0;
          return (
            <li key={dep.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div>
                <div className="font-medium">{longDate(dep.starts_on)} <span className="text-muted-foreground">to</span> {longDate(dep.ends_on)}</div>
                <div className="text-sm text-muted-foreground">{full ? "Fully booked" : `${dep.remaining_seats} of ${dep.capacity} seats left`}</div>
              </div>
              <Button size="sm" disabled={full} onClick={() => setTarget({ pkg, dep })}>
                {full ? "Full" : "Book"}
              </Button>
            </li>
          );
        })}
      </ul>
      <BookingDialog target={target} onClose={() => setTarget(null)} onBooked={() => router.refresh()} />
    </>
  );
}
