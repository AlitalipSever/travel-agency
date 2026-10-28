import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/site/page-header";
import { listDocs } from "@/lib/docs";

export const metadata: Metadata = { title: "Documentation" };

const WHAT: Record<string, string> = {
  "00-domain": "Who the system is for: stakeholders, actors, ubiquitous language, roles, questions for the client",
  "01-requirements": "The brief, every requirement with acceptance checks, the assumptions, the exclusions",
  "02-architecture": "arc42 sections 1 to 12 with C4 diagrams: context, containers, runtime, deployment, quality, risks",
  "03-data-model": "Entities, relations, derived values, constraints, indexes",
  "04-api": "Endpoint list, request and response shapes, error format, auth",
  "05-work-packages": "The work cut into packages as for a team of three, with dependencies and order",
  "06-operations": "Runbook: deploy, rollback, backups, secrets, health, what to look at when something is wrong",
  "07-roadmap": "What is done, what was deliberately left out, the next two weeks",
  "08-walkthrough": "The ten minute walkthrough, in order",
  "arc42-checklist": "Every official arc42 subsection and where it lives",
  "plans/bookable": "The measured query plan of the bookable search",
};

export default async function DocsIndex() {
  const docs = await listDocs();
  return (
    <>
      <PageHeader eyebrow="Documentation" title="Documents" lead="Rendered from the repository's docs/ folder at build time. Decisions have their own section." />
      <div className="mx-auto grid max-w-6xl gap-3 px-4 pb-20 sm:grid-cols-2">
        {docs.map((d) => (
          <Link key={d.slug} href={`/docs/${d.slug}`} className="group rounded-lg border bg-card p-4 transition-colors hover:border-ring">
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium">{d.title}</span>
              <ArrowRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{WHAT[d.slug]}</p>
          </Link>
        ))}
      </div>
    </>
  );
}
