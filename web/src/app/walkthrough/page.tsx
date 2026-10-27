import type { Metadata } from "next";
import { PageHeader } from "@/components/site/page-header";

export const metadata: Metadata = { title: "Walkthrough" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Walkthrough" title="Walkthrough" lead="The ten minute path through the system, in order." />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          This section arrives with work package W6 (docs/05-work-packages.md).
        </p>
      </div>
    </>
  );
}
