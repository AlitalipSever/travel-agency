import type { Metadata } from "next";
import { PageHeader } from "@/components/site/page-header";

export const metadata: Metadata = { title: "Decisions" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Decisions" title="Decisions" lead="Every architecture decision record, with its context, the options and the consequences." />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          This section arrives with work package W2 (docs/05-work-packages.md).
        </p>
      </div>
    </>
  );
}
