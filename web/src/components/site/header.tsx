import Link from "next/link";
import { Menu } from "lucide-react";
import { SECTIONS } from "@/lib/sections";
import { SpectrumBar } from "@/components/spectral/spectrum-bar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { NavLinks } from "@/components/site/nav-links";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2.5 text-foreground">
          <SpectrumBar className="h-4" />
          <span className="text-[15px] font-medium tracking-tight">travel-agency</span>
        </Link>
        <nav className="hidden flex-1 items-center gap-1 md:flex">
          <NavLinks />
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" nativeButton={false} render={<a href="/api/docs-link" />} className="hidden sm:inline-flex">
            Swagger UI
          </Button>
          <Sheet>
            <SheetTrigger render={<Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu" />}>
              <Menu className="size-5" />
            </SheetTrigger>
            <SheetContent side="right" className="w-72">
              <SheetTitle className="label-mono text-muted-foreground">Sections</SheetTitle>
              <nav className="mt-4 flex flex-col gap-1">
                {SECTIONS.map((s) => (
                  <Link key={s.href} href={s.href} className="rounded-md px-3 py-2 text-sm hover:bg-accent">
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
