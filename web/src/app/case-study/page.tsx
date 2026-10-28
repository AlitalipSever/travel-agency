import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Isolines } from "@/components/spectral/isolines";
import { SECTIONS } from "@/lib/sections";
import { ThreeParts } from "@/components/overview/three-parts";
import { HowItIsBuilt } from "@/components/overview/how-it-is-built";

export const metadata = { title: "Case study" };

export default function OverviewPage() {
  return (
    <>
      <section className="relative overflow-hidden bg-spectral-field text-white">
        <Isolines />
        <div className="relative mx-auto max-w-6xl px-4 pt-20 pb-24 sm:pt-28 sm:pb-32">
          <p className="label-mono text-white/80">Behind the site: a backend case study</p>
          <h1 className="mt-4 max-w-2xl text-4xl font-medium leading-[1.05] tracking-tight sm:text-6xl">
            Which tours can be sold between two dates, to travellers who accept this much risk?
          </h1>
          <p className="mt-6 max-w-xl text-lg text-white/85">
            The backend behind Andes &amp; Coast: live weather for the agency&apos;s cities, cities grouped by temperature, tours with a danger score, dated departures with seats, and the search that answers the question above in two queries.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button size="lg" nativeButton={false} className="bg-white text-spectral-night hover:bg-white/90" render={<Link href="/demo" />}>
              Open the live demo <ArrowRight className="size-4" />
            </Button>
            <Button size="lg" variant="outline" nativeButton={false} className="border-white/60 bg-transparent text-white hover:bg-white/10 hover:text-white" render={<Link href="/docs/02-architecture" />}>
              Architecture, arc42
            </Button>
          </div>
        </div>
      </section>

      <ThreeParts />
      <HowItIsBuilt />

      <section className="mx-auto max-w-6xl px-4 pb-20">
        <p className="label-mono text-muted-foreground">Sections</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {SECTIONS.filter((s) => s.href !== "/case-study").map((s) => (
            <Link key={s.href} href={s.href} className="group rounded-lg border bg-card p-4 transition-colors hover:border-ring">
              <div className="flex items-center justify-between">
                <span className="font-medium">{s.label}</span>
                <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{s.short}</p>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
