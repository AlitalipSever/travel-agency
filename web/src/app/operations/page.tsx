import type { Metadata } from "next";
import { PageHeader } from "@/components/site/page-header";

export const metadata: Metadata = { title: "Operations" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Operations" title="Operations" lead="Live numbers of the weather pipeline" />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          This section arrives with work package  last refresh, calls against the budget, breaker state.:W5 (docs/05-work-packages.md).
        </p>
      </div>
    </>
  );
}
