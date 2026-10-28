"use client";

import { useEffect, useState } from "react";
import { demoFetch, DemoError } from "@/lib/demo-client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatTiles } from "@/components/operations/stat-tiles";
import type { OpsStatus } from "@/lib/ops-types";

const EVERY_MS = 30_000;

export function StatusPanel() {
  const [data, setData] = useState<OpsStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    demoFetch<OpsStatus>("ops/status")
      .then((r) => {
        if (cancelled) return;
        setData(r.data);
        setError(null);
        setFetchedAt(new Date());
      })
      .catch((e) => !cancelled && setError(e instanceof DemoError ? `${e.problem.status} ${e.message}` : String(e)));
    const timer = setInterval(() => setTick((t) => t + 1), EVERY_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [tick]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" variant="outline" onClick={() => setTick((t) => t + 1)}>Read again</Button>
        <span className="label-mono text-muted-foreground">
          {fetchedAt ? `read ${fetchedAt.toISOString().slice(11, 19)} UTC · every 30 s` : "reading…"}
        </span>
      </div>
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Status unavailable</AlertTitle>
          <AlertDescription>{error}. The endpoint is `/api/v1/ops/status`; it needs the API with work package B12.</AlertDescription>
        </Alert>
      ) : null}
      {!data && !error ? <Skeleton className="h-64 w-full" /> : null}
      {data ? <StatTiles status={data} /> : null}
    </div>
  );
}
