"use client";

import { useState } from "react";
import { demoFetch, DemoError } from "@/lib/demo-client";
import type { BookableDeparture, BookablePackage, BookableResponse } from "@/lib/demo-types";
import { bracketColour, onSpectrum } from "@/lib/spectrum";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { BookingDialog } from "@/components/demo/booking-dialog";

const DANGER = ["none", "low", "medium", "high"];

export function BookableSearch({ defaultFrom, defaultTo }: { defaultFrom: string; defaultTo: string }) {
  const [from, setFrom] = useState(defaultFrom);
  const [to, setTo] = useState(defaultTo);
  const [danger, setDanger] = useState(2);
  const [exact, setExact] = useState(false);
  const [data, setData] = useState<BookableResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [booking, setBooking] = useState<{ pkg: BookablePackage; dep: BookableDeparture } | null>(null);

  async function search(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const q = new URLSearchParams({ from, to, danger: String(danger), ...(exact ? { danger_mode: "exact" } : {}) });
      setData((await demoFetch<BookableResponse>(`packages/bookable?${q}`)).data);
    } catch (err) {
      setData(null);
      setError(err instanceof DemoError ? `${err.problem.status}: ${err.message}` : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <form onSubmit={search} className="grid gap-3 rounded-lg border bg-card p-4 sm:grid-cols-[1fr_1fr_auto_auto_auto] sm:items-end">
        <div className="grid gap-1.5"><Label htmlFor="from">From</Label><Input id="from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></div>
        <div className="grid gap-1.5"><Label htmlFor="to">To</Label><Input id="to" type="date" value={to} onChange={(e) => setTo(e.target.value)} /></div>
        <div className="grid gap-1.5">
          <Label>Danger</Label>
          <div className="flex gap-1">
            {DANGER.map((label, i) => (
              <button key={label} type="button" onClick={() => setDanger(i)} className={`rounded border px-2 py-1 text-xs ${danger === i ? "ring-2 ring-ring" : ""}`} style={{ background: bracketColour(i, 4), color: onSpectrum(i / 3) }}>
                {i} {label}
              </button>
            ))}
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={exact} onChange={(e) => setExact(e.target.checked)} /> exact</label>
        <Button type="submit" disabled={busy}>{busy ? "Searching…" : "Search"}</Button>
      </form>
      {error ? <Alert variant="destructive"><AlertTitle>Rejected</AlertTitle><AlertDescription>{error}</AlertDescription></Alert> : null}
      {data ? (
        <>
          <p className="label-mono text-muted-foreground">
            {data.count} package{data.count === 1 ? "" : "s"} · today {data.query.today} in {data.query.timezone} · danger {data.query.danger_mode === "exact" ? "exactly" : "at most"} {data.query.danger}
          </p>
          <ul className="grid gap-3 md:grid-cols-2">
            {data.results.map((p) => (
              <li key={p.id} className="rounded-lg border bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-medium">{p.name}</h3>
                    <p className="text-sm text-muted-foreground">{p.duration_days} days · {p.price} {p.currency} per traveller</p>
                  </div>
                  <span className="label-mono rounded px-1.5 py-0.5" style={{ background: bracketColour(p.danger, 4), color: onSpectrum(p.danger / 3) }}>{p.danger} {p.danger_label}</span>
                </div>
                <ul className="mt-3 divide-y rounded-md border">
                  {p.departures.map((d) => (
                    <li key={d.id} className="flex items-center justify-between gap-2 px-3 py-1.5 text-sm">
                      <span>{d.starts_on} → {d.ends_on}</span>
                      <span className="font-mono text-xs text-muted-foreground">{d.remaining_seats} of {d.capacity} left</span>
                      <Button size="sm" variant="outline" onClick={() => setBooking({ pkg: p, dep: d })}>Book</Button>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <BookingDialog target={booking} onClose={() => setBooking(null)} onBooked={() => search()} />
    </div>
  );
}
