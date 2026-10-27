import type { Metadata } from "next";
import { PageHeader } from "@/components/site/page-header";

export const metadata: Metadata = { title: "Plan" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Plan" title="Plan" lead="The work cut into packages for a team of three, what is done and what comes next." />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          This section arrives with work package W4 (docs/05-work-packages.md).
        </p>
      </div>
    </>
  );
}
