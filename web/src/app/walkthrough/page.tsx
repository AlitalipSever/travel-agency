import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { connection } from "next/server";
import { PageHeader } from "@/components/site/page-header";
import { Deck } from "@/components/walkthrough/deck";
import { Markdown } from "@/components/docs/markdown";
import { BracketsPanel } from "@/components/demo/brackets-panel";
import { BookableSearch } from "@/components/demo/bookable-search";
import { StatusPanel } from "@/components/operations/status-panel";
import { daysFromNow } from "@/lib/demo-client";
import { docSection, walkthroughSteps } from "@/lib/walkthrough";
import { listAdrs } from "@/lib/docs";

export const metadata: Metadata = { title: "Walkthrough" };

const PROSE = "prose prose-neutral dark:prose-invert max-w-none prose-headings:font-medium prose-headings:tracking-tight prose-a:text-spectral-sky prose-pre:bg-muted prose-pre:text-foreground";

function Links({ items }: { items: [string, string][] }) {
  return (
    <ul className="flex flex-wrap gap-2">
      {items.map(([href, label]) => (
        <li key={href}>
          <Link href={href} className="inline-block rounded-md border bg-card px-3 py-1.5 text-sm hover:border-ring">{label}</Link>
        </li>
      ))}
    </ul>
  );
}

async function Search() {
  await connection();
  return <BookableSearch defaultFrom={daysFromNow(1)} defaultTo={daysFromNow(90)} />;
}

export default async function WalkthroughPage() {
  const [steps, summary, adrs] = await Promise.all([walkthroughSteps(), docSection("02-architecture", "0."), listAdrs()]);
  const decisions = adrs.filter((a) => ["0002", "0003", "0005", "0012"].includes(a.id));
  const extras = [
    <BracketsPanel key="1" />,
    <Links key="2" items={[["/docs/00-domain#7-questions-i-would-ask-the-client-first", "00 Domain §7: questions and the assumption"], ["/docs/01-requirements#3-assumptions-gaps-in-the-brief-how-we-fill-them", "01 Requirements §3: the seventeen assumptions"]]} />,
    <div key="3" className={PROSE}><Markdown body={summary} from="docs" /></div>,
    <Links key="4" items={decisions.map((a) => [`/decisions/${a.id}`, `ADR ${a.id} ${a.title}`] as [string, string]).concat([["/plan", "07 §4: the signals that would change them"]])} />,
    <Links key="5" items={[["/demo", "source, stale, partial on the demo"], ["/docs/02-architecture#11-risks-and-technical-debt", "02 §11 risks"], ["/docs/07-roadmap#2-deliberately-left-out", "07 §2 deliberately left out"]]} />,
    <StatusPanel key="6" />,
    <Suspense key="7" fallback={<div className="h-24 rounded-lg border bg-card" />}><Search /></Suspense>,
    <Links key="8" items={[["/plan", "Roadmap: the next two weeks, how the team grows"]]} />,
    <p key="9" className="text-lg text-muted-foreground">Thank you.</p>,
  ];
  return (
    <>
      <PageHeader
        eyebrow="Walkthrough"
        title="Ten minutes, in order"
        lead="The ten minute path through the system, one step per screen. Arrow keys or space move between steps; F toggles full screen."
      />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <Deck steps={steps} extras={extras} />
      </div>
    </>
  );
}
