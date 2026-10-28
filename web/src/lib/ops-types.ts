export type RefreshRun = {
  run_id: string;
  trigger: string;
  started_at: string;
  finished_at: string | null;
  locations: number;
  calls_used: number;
  failures: number;
  effective_interval_s: number | null;
  notes: string;
};

export type OpsStatus = {
  last_run: RefreshRun | null;
  last_finished_run: RefreshRun | null;
  configured_interval_s: number;
  upstream: { minute: Record<"refresh" | "adhoc", { used: number; limit: number }>; month: { used: number; limit: number } };
  breaker: { state: string; consecutive_failures: number; open_for_s: number; threshold: number; cooldown_s: number };
  adhoc_cache: { hits: number; misses: number; hit_ratio: number | null };
  samples: { count: number; retention_days: number | null };
  versions: { api: string | null; commit: string | null; chart: string | null };
};
