import type { OpsStatus } from "@/lib/ops-types";
import { spectrum, onSpectrum } from "@/lib/spectrum";

function ago(iso: string | null): string {
  if (!iso) return "never";
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 90) return `${s} s ago`;
  if (s < 5400) return `${Math.round(s / 60)} min ago`;
  return `${(s / 3600).toFixed(1)} h ago`;
}

/** A share drawn as a spectrum bar: the fill level is the fraction used, cool when idle, warm when near the limit. */
function Share({ label, used, limit }: { label: string; used: number; limit: number }) {
  const t = limit ? Math.min(1, used / limit) : 0;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="label-mono text-muted-foreground">{label}</span>
        <span className="font-mono text-sm">{used} / {limit}</span>
      </div>
      <div className="mt-1 h-3 overflow-hidden rounded-sm border bg-spectral-night/90">
        <div className="h-full" style={{ width: `${t * 100}%`, background: spectrum(t) }} />
      </div>
    </div>
  );
}

function Tile({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="label-mono text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-medium tracking-tight">{value}</p>
      {sub ? <p className="mt-1 text-xs text-muted-foreground">{sub}</p> : null}
    </div>
  );
}

export function StatTiles({ status }: { status: OpsStatus }) {
  const run = status.last_finished_run;
  const breakerT = status.breaker.state === "closed" ? 0.1 : status.breaker.state === "half_open" ? 0.75 : 0.95;
  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="Last refresh" value={ago(run?.finished_at ?? null)} sub={run ? `${run.trigger} · ${run.locations} locations · ${run.calls_used} calls · ${run.failures} failed` : "no finished run yet"} />
        <Tile label="Effective interval" value={`${run?.effective_interval_s ?? status.configured_interval_s} s`} sub={`configured ${status.configured_interval_s} s; lengthened when the budget would be exceeded`} />
        <Tile
          label="Circuit breaker"
          value={<span className="rounded px-2 py-0.5 text-lg" style={{ background: spectrum(breakerT), color: onSpectrum(breakerT) }}>{status.breaker.state}</span>}
          sub={`${status.breaker.consecutive_failures} consecutive failures of ${status.breaker.threshold}${status.breaker.open_for_s ? ` · open for ${status.breaker.open_for_s} s` : ""}`}
        />
        <Tile label="Stored samples" value={status.samples.count.toLocaleString("en")} sub={`kept ${status.samples.retention_days ?? "?"} days`} />
      </div>
      <div className="grid gap-6 rounded-lg border bg-card p-4 md:grid-cols-3">
        <Share label="Refresh share, this minute" used={status.upstream.minute.refresh.used} limit={status.upstream.minute.refresh.limit} />
        <Share label="Ad hoc share, this minute" used={status.upstream.minute.adhoc.used} limit={status.upstream.minute.adhoc.limit} />
        <Share label="Month" used={status.upstream.month.used} limit={status.upstream.month.limit} />
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Tile label="Ad hoc cache" value={status.adhoc_cache.hit_ratio == null ? "–" : `${Math.round(status.adhoc_cache.hit_ratio * 100)} %`} sub={`${status.adhoc_cache.hits} hits · ${status.adhoc_cache.misses} upstream calls, last seven days`} />
        <Tile label="Versions" value={<span className="font-mono text-base">api {status.versions.api ?? "?"}</span>} sub={`commit ${status.versions.commit?.slice(0, 7) ?? "not set"} · chart ${status.versions.chart ?? "not set"}`} />
        <Tile label="Last run notes" value={<span className="text-base">{run?.notes || "none"}</span>} sub={run ? `started ${run.started_at.slice(11, 19)} UTC` : undefined} />
      </div>
    </div>
  );
}
