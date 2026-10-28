import Link from "next/link";
import { AGENCY } from "@/lib/agency";
import { SpectrumBar } from "@/components/spectral/spectrum-bar";

export function SiteFooter() {
  return (
    <footer className="border-t bg-muted/30">
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-10 text-sm text-muted-foreground sm:grid-cols-3">
        <div>
          <div className="flex items-center gap-2 text-foreground">
            <SpectrumBar className="h-3 w-8" level={0.4} />
            <span className="font-semibold">{AGENCY.name}</span>
          </div>
          <p className="mt-2 max-w-xs">{AGENCY.tagline}. Thirteen capitals, live weather, small groups.</p>
        </div>
        <div>
          <p className="font-medium text-foreground">Please note</p>
          <p className="mt-2 max-w-xs">{AGENCY.demoNote}</p>
          <p className="mt-1 max-w-xs">The photos are AI-made and show the mood of a place, not an exact view.</p>
        </div>
        <div>
          <p className="font-medium text-foreground">Behind the site</p>
          <ul className="mt-2 space-y-1">
            <li><Link href="/case-study" className="hover:text-foreground">The case study</Link></li>
            <li><Link href="/operations" className="hover:text-foreground">Live operations status</Link></li>
            <li><a href="/api/docs-link" className="hover:text-foreground">API (Swagger UI)</a></li>
          </ul>
          <p className="label-mono mt-4">Weather by OpenWeatherMap</p>
        </div>
      </div>
    </footer>
  );
}
