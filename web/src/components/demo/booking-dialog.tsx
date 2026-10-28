"use client";

import { useEffect, useState } from "react";
import { demoFetch, DemoError } from "@/lib/demo-client";
import type { BookableDeparture, BookablePackage, Booking, Page, Traveller } from "@/lib/demo-types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

type Target = { pkg: BookablePackage; dep: BookableDeparture } | null;
type Outcome = { kind: "ok"; booking: Booking; replayed: boolean } | { kind: "problem"; status: number; detail: string };

export function BookingDialog({ target, onClose, onBooked }: { target: Target; onClose: () => void; onBooked: () => void }) {
  return (
    <Dialog open={!!target} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        {target ? <BookingForm key={target.dep.id} target={target} onBooked={onBooked} /> : null}
      </DialogContent>
    </Dialog>
  );
}

/** Remounted per departure (key), so every state starts clean without resets in effects. */
function BookingForm({ target, onBooked }: { target: NonNullable<Target>; onBooked: () => void }) {
  const [travellers, setTravellers] = useState<Traveller[]>([]);
  const [travellerId, setTravellerId] = useState("");
  const [newName, setNewName] = useState("");
  const [seats, setSeats] = useState(1);
  const [key] = useState(() => crypto.randomUUID());
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    demoFetch<Page<Traveller>>("travellers?page_size=50").then((r) => {
      if (cancelled) return;
      setTravellers(r.data.results);
      setTravellerId(r.data.results[0]?.id ?? "");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(replay = false) {
    setBusy(true);
    try {
      let tid = travellerId;
      if (!tid && newName.trim()) {
        tid = (await demoFetch<Traveller>("travellers", { method: "POST", body: JSON.stringify({ name: newName.trim() }), headers: { "Content-Type": "application/json" } })).data.id;
        setTravellerId(tid);
      }
      const r = await demoFetch<Booking>("bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": key },
        body: JSON.stringify({ departure_id: target.dep.id, traveller_id: tid, seats }),
      });
      setOutcome({ kind: "ok", booking: r.data, replayed: r.status === 200 || r.headers.get("idempotent-replayed") === "true" });
      if (!replay) onBooked();
    } catch (e) {
      if (e instanceof DemoError) setOutcome({ kind: "problem", status: e.problem.status, detail: e.message });
      else setOutcome({ kind: "problem", status: 0, detail: String(e) });
    } finally {
      setBusy(false);
    }
  }

  async function cancel(id: string) {
    setBusy(true);
    try {
      const r = await demoFetch<Booking>(`bookings/${id}/cancel`, { method: "POST" });
      setOutcome({ kind: "ok", booking: r.data, replayed: false });
      onBooked();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
        <DialogHeader>
          <DialogTitle>{target.pkg.name}</DialogTitle>
          <DialogDescription>
            {target.dep.starts_on} to {target.dep.ends_on} · {target.dep.remaining_seats} of {target.dep.capacity} seats left · {target.pkg.price} {target.pkg.currency} per traveller
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="traveller">Traveller</Label>
            <select id="traveller" className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm" value={travellerId} onChange={(e) => setTravellerId(e.target.value)}>
              {travellers.map((t) => (
                <option key={t.id} value={t.id}>{t.name}{t.risk_appetite != null ? ` (risk appetite ${t.risk_appetite})` : ""}</option>
              ))}
              <option value="">New traveller…</option>
            </select>
            {!travellerId ? <Input placeholder="Name" value={newName} onChange={(e) => setNewName(e.target.value)} /> : null}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="seats">Seats</Label>
            <Input id="seats" type="number" min={1} max={40} value={seats} onChange={(e) => setSeats(Math.max(1, +e.target.value))} className="w-24" />
          </div>
          <p className="label-mono text-muted-foreground">Idempotency-Key {key.slice(0, 8)}…</p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => submit()} disabled={busy || (!travellerId && !newName.trim())}>Book {seats} seat{seats === 1 ? "" : "s"}</Button>
            {outcome?.kind === "ok" && outcome.booking.status === "confirmed" ? (
              <>
                <Button variant="outline" onClick={() => submit(true)} disabled={busy}>Send again (same key)</Button>
                <Button variant="outline" onClick={() => cancel(outcome.booking.id)} disabled={busy}>Cancel booking</Button>
              </>
            ) : null}
          </div>
          {outcome?.kind === "ok" ? (
            <div className="rounded-md border bg-muted p-3 text-sm">
              <p className="font-medium">{outcome.booking.status === "confirmed" ? (outcome.replayed ? "200 replayed: the same booking, no second row" : "201 confirmed") : "200 cancelled, seats freed"}</p>
              <p className="font-mono text-xs text-muted-foreground">
                {outcome.booking.id.slice(0, 8)} · {outcome.booking.seats} seat(s) · {outcome.booking.price_at_booking} {outcome.booking.currency} · danger at booking {outcome.booking.danger_at_booking}
              </p>
            </div>
          ) : null}
          {outcome?.kind === "problem" ? (
            <div className="rounded-md border border-destructive/50 bg-destructive/5 p-3 text-sm">
              <p className="font-medium">{outcome.status === 409 ? "409 conflict: not enough seats" : `${outcome.status}`}</p>
              <p className="text-muted-foreground">{outcome.detail}</p>
            </div>
          ) : null}
        </div>
    </>
  );
}
