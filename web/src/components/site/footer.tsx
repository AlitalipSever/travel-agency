import { SpectrumBar } from "@/components/spectral/spectrum-bar";

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2.5">
          <SpectrumBar className="h-3.5" level={0.4} />
          <span>Travel agency backend, a case study. Django, Django REST Framework, Celery, PostgreSQL, Redis, Next.js.</span>
        </div>
        <span className="label-mono">Weather by OpenWeatherMap</span>
      </div>
    </footer>
  );
}
