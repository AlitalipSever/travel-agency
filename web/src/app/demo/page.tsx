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
        title="The API at work: weather, search, booking"
        lead="Every call on this page goes to the API as the demo partner. The site adds the token on the server, so it never reaches the browser. Demo data is separate and reset every night."
      />
      <div className="mx-auto max-w-6xl space-y-14 px-4 pb-20">
        <section>
          <h2 className="text-xl font-medium tracking-tight">Locations by temperature bracket</h2>
          <p className="mt-1 mb-5 max-w-2xl text-sm text-muted-foreground">
            Thirteen capitals, each in one temperature group by its latest reading. The group edges come from settings; quantile mode sets them from today's readings so no group is empty. Old readings and cities without a reading are shown, not hidden. Click a city for its forecast, or any other point on the map for the weather there right now.
          </p>
          <BracketsPanel />
        </section>
        <section>
          <h2 className="text-xl font-medium tracking-tight">Bookable packages</h2>
          <p className="mt-1 mb-5 max-w-2xl text-sm text-muted-foreground">
            Tours with a danger score up to (or exactly) the one you pick, with a planned date in the range, from today on, with seats left. Each result lists only the dates that matched. Book one, send the same request twice to see the replay, or sell a date out to get the 409.
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
