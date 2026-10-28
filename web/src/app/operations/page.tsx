import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/site/page-header";
import { StatusPanel } from "@/components/operations/status-panel";

export const metadata: Metadata = { title: "Operations" };

export default function OperationsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Operations"
        title="The weather pipeline, live"
        lead="Live numbers from the API: the last weather refresh, calls against the budget, the circuit breaker, the cache, and which version is running."
      />
      <div className="mx-auto max-w-6xl space-y-8 px-4 pb-20">
        <StatusPanel />
        <p className="text-sm text-muted-foreground">
          What to do when a number looks wrong is in the runbook: <Link href="/docs/06-operations" className="text-spectral-sky hover:underline">06-operations §10</Link>.
        </p>
      </div>
    </>
  );
}
