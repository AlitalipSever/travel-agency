import { levelLabel } from "@/lib/agency";
import { cn } from "@/lib/utils";

const TONE = ["bg-emerald-50 text-emerald-800 ring-emerald-200", "bg-sky-50 text-sky-800 ring-sky-200", "bg-amber-50 text-amber-800 ring-amber-200", "bg-rose-50 text-rose-800 ring-rose-200"];

/** Adventure level 0 to 3 as a small coloured chip. */
export function LevelBadge({ score, className }: { score: number; className?: string }) {
  const i = Math.min(Math.max(score, 0), 3);
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset", TONE[i], className)}>
      {levelLabel(i)}
    </span>
  );
}
