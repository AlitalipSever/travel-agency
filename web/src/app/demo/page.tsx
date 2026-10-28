import type { Metadata } from "next";
import { Suspense } from "react";
import { connection } from "next/server";
import { daysFromNow } from "@/lib/demo-client";
import { PageHeader } from "@/components/site/page-header";
import { BracketsPanel } from "@/components/demo/brackets-panel";
import { BookableSearch } from "@/components/demo/bookable-search";

export const metadata: Metadata = { title: "Live demo" };

export default function DemoPage() {
  return (
    <>
      <PageHeader
        eyebrow="Live demo"
        title="Brackets, forecasts, the bookable search, a booking"
        lead="Every call below goes to the API as the demo partner through the site's own proxy; the token never reaches the browser. Demo data is isolated and reset nightly."
      />
      <div className="mx-auto max-w-6xl space-y-14 px-4 pb-20">
        <section>
          <h2 className="text-xl font-medium tracking-tight">Locations by temperature bracket</h2>
          <p className="mt-1 mb-5 max-w-2xl text-sm text-muted-foreground">
            Thirteen capitals, each in exactly one half-open bracket by its latest observation. Fixed edges come from the settings table; quantile mode derives them from today&apos;s readings so no bracket is empty. Stale readings and locations without a reading are shown, not hidden. Click a point for its forecast, or any other place on the map for the current weather at that coordinate through the ad hoc path (cache, live, stale, 503).
          </p>
          <BracketsPanel />
        </section>
        <section>
          <h2 className="text-xl font-medium tracking-tight">Bookable packages</h2>
          <p className="mt-1 mb-5 max-w-2xl text-sm text-muted-foreground">
            Packages whose derived danger is at most (or exactly) the score, with a planned departure inside the range, on or after today in the agency&apos;s time zone, with seats left. Each result lists only the departures that matched. Book one, send the same request again to see the idempotent replay, or sell a departure out to get the 409.
          </p>
          <Suspense fallback={<div className="h-24 rounded-lg border bg-card" />}>
            <SearchWithDefaults />
          </Suspense>
        </section>
      </div>
    </>
  );
}

/** Default dates come from the request's clock, so this part renders at request time. */
async function SearchWithDefaults() {
  await connection();
  return <BookableSearch defaultFrom={daysFromNow(1)} defaultTo={daysFromNow(90)} />;
}
