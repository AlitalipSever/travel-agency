"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Maximize2, Minimize2, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { spectrum } from "@/lib/spectrum";
import type { Step } from "@/lib/walkthrough";

/** Full screen, keyboard driven: ← → or space move, Home/End jump, F toggles full screen. */
export function Deck({ steps, extras }: { steps: Step[]; extras: ReactNode[] }) {
  const [i, setI] = useState(0);
  const [full, setFull] = useState(false);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState<number | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const last = steps.length - 1;

  const go = useCallback(
    (next: number) => {
      setI(Math.max(0, Math.min(last, next)));
      setStartedAt((s) => s ?? Date.now());
    },
    [last],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === "INPUT" || (e.target as HTMLElement)?.tagName === "SELECT") return;
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") go(i + 1);
      else if (e.key === "ArrowLeft" || e.key === "PageUp") go(i - 1);
      else if (e.key === "Home") go(0);
      else if (e.key === "End") go(last);
      else if (e.key.toLowerCase() === "f") toggleFull();
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  useEffect(() => {
    const onChange = () => setFull(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onChange);
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => {
      document.removeEventListener("fullscreenchange", onChange);
      clearInterval(t);
    };
  }, []);

  function toggleFull() {
    if (document.fullscreenElement) document.exitFullscreen();
    else root.current?.requestFullscreen?.();
  }

  const step = steps[i];
  const elapsed = startedAt && now ? Math.round((now - startedAt) / 1000) : 0;
  const t = Math.min(1, elapsed / 600);

  return (
    <div ref={root} className={`flex flex-col bg-background text-foreground ${full ? "h-screen overflow-y-auto p-6" : "min-h-[70vh] rounded-lg border p-4 sm:p-6"}`}>
      <div className="flex items-center gap-3">
        <span className="label-mono text-muted-foreground">step {step.n} of {steps.length}</span>
        {step.budget ? <span className="label-mono rounded border px-1.5 py-0.5 text-muted-foreground">{step.budget}</span> : null}
        <span className="label-mono text-muted-foreground">{startedAt ? `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")} of 10:00` : "press → to start the clock"}</span>
        <div className="ml-auto flex items-center gap-1">
          <Button size="icon-sm" variant="ghost" aria-label="Previous" onClick={() => go(i - 1)}><ChevronLeft className="size-4" /></Button>
          <Button size="icon-sm" variant="ghost" aria-label="Next" onClick={() => go(i + 1)}><ChevronRight className="size-4" /></Button>
          <Button size="icon-sm" variant="ghost" aria-label="Toggle full screen" onClick={toggleFull}>{full ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}</Button>
        </div>
      </div>
      <div className="mt-3 h-1 w-full overflow-hidden rounded bg-muted">
        <div className="h-full transition-[width] duration-1000" style={{ width: `${t * 100}%`, background: spectrum(t) }} />
      </div>
      <div className="mt-8 flex-1">
        <p className="label-mono text-muted-foreground">Walkthrough</p>
        <h2 className="mt-2 max-w-3xl text-3xl font-medium tracking-tight sm:text-5xl">{step.title}</h2>
        {step.text ? <p className="mt-4 max-w-3xl text-lg text-muted-foreground">{step.text}</p> : null}
        <div className="mt-8">{extras[i]}</div>
      </div>
      <ol className="mt-8 flex flex-wrap gap-1.5">
        {steps.map((s, k) => (
          <li key={s.n}>
            <button type="button" onClick={() => go(k)} className={`label-mono rounded px-2 py-1 ${k === i ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-accent"}`}>
              {s.n} {s.title.split(/[,:.]/)[0].slice(0, 22)}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
