import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { DocPage } from "@/components/docs/doc-page";
import { docSlugs, getDoc } from "@/lib/docs";

export async function generateStaticParams() {
  return docSlugs().map((slug) => ({ slug: slug.split("/") }));
}

type Props = { params: Promise<{ slug: string[] }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const doc = await getDoc((await params).slug.join("/"));
  return { title: doc?.title ?? "Document" };
}

// The params read sits behind Suspense so the route's app shell stays URL independent.
async function Document({ params }: Props) {
  const doc = await getDoc((await params).slug.join("/"));
  if (!doc) notFound();
  return <DocPage doc={doc} from="docs" eyebrow="Documentation" back={{ href: "/docs", label: "All documents" }} />;
}

export default function Page({ params }: Props) {
  return (
    <Suspense fallback={<div className="mx-auto max-w-6xl px-4 py-10 text-sm text-muted-foreground">Loading…</div>}>
      <Document params={params} />
    </Suspense>
  );
}
