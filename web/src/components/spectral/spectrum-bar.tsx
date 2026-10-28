import { cn } from "@/lib/utils";

/**
 * The brand mark: a battery read as a bar, filled with the spectrum to its level, white ticks
 * at the knees (10 % and 90 %). `level` is 0 to 1.
 */
export function SpectrumBar({
  level = 0.72,
  className,
  title = "Spectrum bar",
}: {
  level?: number;
  className?: string;
  title?: string;
}) {
  const fill = Math.max(0, Math.min(1, level)) * 100;
  return (
    <svg viewBox="0 0 120 36" className={cn("h-5 w-auto", className)} role="img" aria-label={title}>
      <defs>
        <linearGradient id="spectrum" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="var(--spectral-deep)" />
          <stop offset="0.3" stopColor="var(--spectral-sky)" />
          <stop offset="0.5" stopColor="var(--spectral-cyan)" />
          <stop offset="0.65" stopColor="var(--spectral-haze)" />
          <stop offset="0.8" stopColor="var(--spectral-apricot)" />
          <stop offset="0.92" stopColor="var(--spectral-flame)" />
          <stop offset="1" stopColor="var(--spectral-ember)" />
        </linearGradient>
        <clipPath id="spectrum-level">
          <rect x="3" y="3" width={fill * 1.08} height="30" />
        </clipPath>
      </defs>
      <rect x="1.5" y="1.5" width="111" height="33" rx="4" fill="none" stroke="currentColor" strokeWidth="2" />
      <rect x="114" y="11" width="5" height="14" rx="1.5" fill="currentColor" />
      <rect x="3" y="3" width="108" height="30" rx="2.5" fill="url(#spectrum)" clipPath="url(#spectrum-level)" />
      <line x1="13.8" x2="13.8" y1="3" y2="33" stroke="#fff" strokeWidth="1.5" />
      <line x1="100.2" x2="100.2" y1="3" y2="33" stroke="#fff" strokeWidth="1.5" />
    </svg>
  );
}
