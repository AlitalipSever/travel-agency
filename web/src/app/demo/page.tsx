import type { Metadata } from "next";
import { PageHeader } from "@/components/site/page-header";

export const metadata: Metadata = { title: "Live demo" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Live demo" title="Live demo" lead="Brackets, forecasts and the bookable search, run against the API as the demo partner." />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          This section arrives with work package W3 (docs/05-work-packages.md).
        </p>
      </div>
    </>
  );
}
