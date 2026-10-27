import { cn } from "@/lib/utils";

/** Thin white contour lines, the brand's own mark over a spectral field. Decorative. */
export function Isolines({ className }: { className?: string }) {
  const paths = [
    "M-20 120 C 120 60, 260 160, 420 90 S 700 40, 900 120 S 1180 220, 1300 140",
    "M-20 180 C 140 120, 280 220, 440 150 S 720 100, 920 180 S 1200 280, 1300 200",
    "M-20 240 C 160 180, 300 280, 460 210 S 740 160, 940 240 S 1220 340, 1300 260",
    "M-20 300 C 180 240, 320 340, 480 270 S 760 220, 960 300 S 1240 400, 1300 320",
    "M-20 360 C 200 300, 340 400, 500 330 S 780 280, 980 360 S 1260 460, 1300 380",
    "M-20 420 C 220 360, 360 460, 520 390 S 800 340, 1000 420 S 1280 520, 1300 440",
    "M-20 480 C 240 420, 380 520, 540 450 S 820 400, 1020 480 S 1300 580, 1300 500",
  ];
  return (
    <svg
      viewBox="0 0 1280 520"
      preserveAspectRatio="none"
      aria-hidden="true"
      className={cn("pointer-events-none absolute inset-0 h-full w-full", className)}
    >
      {paths.map((d, i) => (
        <path key={i} d={d} fill="none" stroke="#fff" strokeOpacity={0.35 - i * 0.03} strokeWidth="1" />
      ))}
    </svg>
  );
}
