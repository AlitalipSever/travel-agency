"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Search } from "lucide-react";
import { LEVELS } from "@/lib/agency";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Date range and adventure level; the tours page does the search. */
export function HeroSearch({ defaultFrom, defaultTo, defaultLevel = 2 }: { defaultFrom: string; defaultTo: string; defaultLevel?: number }) {
  const router = useRouter();
  const [from, setFrom] = useState(defaultFrom);
  const [to, setTo] = useState(defaultTo);
  const [level, setLevel] = useState(defaultLevel);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        router.push(`/tours?from=${from}&to=${to}&level=${level}`);
      }}
      className="grid gap-3 rounded-xl border bg-background p-4 text-foreground shadow-lg sm:grid-cols-[1fr_1fr_1.4fr_auto] sm:items-end"
    >
      <div>
        <Label htmlFor="from" className="text-xs">From</Label>
        <Input id="from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="mt-1" />
      </div>
      <div>
        <Label htmlFor="to" className="text-xs">To</Label>
        <Input id="to" type="date" value={to} onChange={(e) => setTo(e.target.value)} className="mt-1" />
      </div>
      <div>
        <Label className="text-xs">Adventure level, up to</Label>
        <div className="mt-1 grid grid-cols-4 gap-1">
          {LEVELS.map((l) => (
            <button
              key={l.score}
              type="button"
              onClick={() => setLevel(l.score)}
              title={l.hint}
              className={`rounded-md border px-2 py-2 text-xs ${level === l.score ? "border-spectral-sky bg-spectral-sky text-white" : "bg-background hover:bg-accent"}`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>
      <Button type="submit" size="lg" className="sm:h-10">
        <Search className="size-4" /> Search
      </Button>
    </form>
  );
}
