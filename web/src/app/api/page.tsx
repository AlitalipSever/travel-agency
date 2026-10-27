import type { Metadata } from "next";
import { PageHeader } from "@/components/site/page-header";

export const metadata: Metadata = { title: "API" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="API" title="API" lead="The OpenAPI contract of the backend, browsable from here." />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <p className="rounded-lg border border-dashed p-6 text-sm text-muted-foreground">
          This section arrives with work package W4 (docs/05-work-packages.md).
        </p>
      </div>
    </>
  );
}
