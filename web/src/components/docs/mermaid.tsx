"use client";

import { useEffect, useId, useRef, useState } from "react";

/** Renders a Mermaid source block in the browser, following the site's light or dark theme. */
export function Mermaid({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const mermaid = (await import("mermaid")).default;
      const dark = document.documentElement.classList.contains("dark");
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: dark ? "dark" : "neutral",
        fontFamily: "var(--font-sans)",
        flowchart: { curve: "basis", htmlLabels: true },
      });
      try {
        const { svg } = await mermaid.render(`m${id}`, chart);
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  if (error) {
    return (
      <pre className="overflow-x-auto rounded-md border border-destructive/40 bg-muted p-3 text-xs">
        Diagram failed to render: {error}
        {"\n\n"}
        {chart}
      </pre>
    );
  }
  return <div ref={ref} className="mermaid my-6 overflow-x-auto [&_svg]:mx-auto [&_svg]:max-w-full" />;
}
