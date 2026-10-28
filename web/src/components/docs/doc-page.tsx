import Link from "next/link";
import { Markdown } from "@/components/docs/markdown";
import { Toc } from "@/components/docs/toc";
import type { Doc } from "@/lib/docs";

export function DocPage({
  doc,
  from,
  eyebrow,
  back,
}: {
  doc: Doc;
  from: "docs" | "adr";
  eyebrow: string;
  back: { href: string; label: string };
}) {
  return (
    <div className="mx-auto max-w-6xl px-4 pt-8 pb-20 lg:grid lg:grid-cols-[1fr_240px] lg:gap-10">
      <article className="min-w-0">
        <Link href={back.href} className="label-mono text-muted-foreground hover:text-foreground">
          ← {back.label}
        </Link>
        <p className="label-mono mt-6 text-muted-foreground">{eyebrow}</p>
        <h1 className="mt-2 text-3xl font-medium tracking-tight sm:text-4xl">{doc.title}</h1>
        {doc.status ? <p className="mt-2 font-mono text-xs text-muted-foreground">Status: {doc.status}</p> : null}
        <div className="prose prose-neutral dark:prose-invert mt-8 max-w-none prose-headings:scroll-mt-20 prose-headings:font-medium prose-headings:tracking-tight prose-a:text-spectral-sky prose-code:before:content-none prose-code:after:content-none prose-pre:bg-muted prose-pre:text-foreground">
          <Markdown body={doc.body} from={from} />
        </div>
      </article>
      <Toc headings={doc.headings} />
    </div>
  );
}
