import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { DocPage } from "@/components/docs/doc-page";
import { getAdr, listAdrs } from "@/lib/docs";

export async function generateStaticParams() {
  return (await listAdrs()).map((a) => ({ id: a.id }));
}

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const adr = await getAdr((await params).id);
  return { title: adr ? `ADR ${adr.slug} ${adr.title}` : "Decision" };
}

async function Decision({ params }: Props) {
  const { id } = await params;
  const adr = await getAdr(id);
  if (!adr) notFound();
  return <DocPage doc={adr} from="adr" eyebrow={`ADR ${id}`} back={{ href: "/decisions", label: "All decisions" }} />;
}

export default function Page({ params }: Props) {
  return (
    <Suspense fallback={<div className="mx-auto max-w-6xl px-4 py-10 text-sm text-muted-foreground">Loading…</div>}>
      <Decision params={params} />
    </Suspense>
  );
}
