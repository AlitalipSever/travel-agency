import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/site/page-header";
import { Badge } from "@/components/ui/badge";
import { listAdrs } from "@/lib/docs";

export const metadata: Metadata = { title: "Decisions" };

function tone(status: string): "default" | "secondary" | "outline" {
  if (status.startsWith("accepted")) return "default";
  if (status.startsWith("proposed")) return "secondary";
  return "outline";
}

export default async function DecisionsPage() {
  const adrs = await listAdrs();
  return (
    <>
      <PageHeader
        eyebrow="Decisions"
        title="Architecture decision records"
        lead="One record per important decision: the situation, the options, the choice and what follows from it. A record is not edited after it is accepted; a new one replaces it."
      />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <ol className="divide-y rounded-lg border bg-card">
          {adrs.map((a) => (
            <li key={a.id}>
              <Link href={`/decisions/${a.id}`} className="flex items-start gap-4 px-4 py-3 transition-colors hover:bg-accent/60">
                <span className="label-mono pt-1 text-muted-foreground">{a.id}</span>
                <span className="flex-1">{a.title}</span>
                <Badge variant={tone(a.status)} className="shrink-0">{a.status.replace(/\s*\(.*\)/, "")}</Badge>
              </Link>
            </li>
          ))}
        </ol>
      </div>
    </>
  );
}
