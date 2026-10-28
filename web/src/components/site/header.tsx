import Link from "next/link";
import { Suspense } from "react";
import { Menu } from "lucide-react";
import { AGENCY, AGENCY_NAV } from "@/lib/agency";
import { SECTIONS } from "@/lib/sections";
import { SpectrumBar } from "@/components/spectral/spectrum-bar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { NavLinks } from "@/components/site/nav-links";
import { CaseStudyMenu } from "@/components/agency/case-study-menu";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2.5 text-foreground">
          <SpectrumBar className="h-3.5 w-10" />
          <span className="text-lg font-semibold tracking-tight">{AGENCY.name}</span>
        </Link>
        <nav className="hidden flex-1 items-center gap-1 md:flex">
          <Suspense fallback={null}>
            <NavLinks />
          </Suspense>
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" nativeButton={false} render={<Link href="/tours" />} className="hidden sm:inline-flex">
            Find a tour
          </Button>
          <CaseStudyMenu />
          <Sheet>
            <SheetTrigger render={<Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu" />}>
              <Menu className="size-5" />
            </SheetTrigger>
            <SheetContent side="right" className="w-72">
              <SheetTitle className="text-base font-semibold">{AGENCY.name}</SheetTitle>
              <nav className="mt-4 flex flex-col gap-1">
                {AGENCY_NAV.map((s) => (
                  <Link key={s.href} href={s.href} className="rounded-md px-3 py-2 text-sm hover:bg-accent">
                    {s.label}
                  </Link>
                ))}
              </nav>
              <p className="label-mono mt-6 px-3 text-muted-foreground">Case study</p>
              <nav className="mt-2 flex flex-col gap-1">
                {SECTIONS.map((s) => (
                  <Link key={s.href} href={s.href} className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent">
                    {s.label}
                  </Link>
                ))}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
