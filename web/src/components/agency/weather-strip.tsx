import Link from "next/link";
import type { BracketsResponse } from "@/lib/demo-types";

/** Today's temperatures in three plain groups, from the brackets endpoint. */
export function WeatherStrip({ data }: { data: BracketsResponse }) {
  const all = data.brackets.flatMap((b) => b.locations);
  const groups = [
    { title: "Warm now", hint: "25° and above", items: all.filter((l) => l.temp >= 25) },
    { title: "Mild now", hint: "15° to 25°", items: all.filter((l) => l.temp >= 15 && l.temp < 25) },
    { title: "Cool now", hint: "under 15°", items: all.filter((l) => l.temp < 15) },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {groups.map((g) => (
        <div key={g.title} className="rounded-xl border bg-card p-4">
          <div className="flex items-baseline justify-between">
            <h3 className="font-semibold">{g.title}</h3>
            <span className="text-xs text-muted-foreground">{g.hint}</span>
          </div>
          <ul className="mt-3 space-y-1.5 text-sm">
            {g.items.length === 0 ? <li className="text-muted-foreground">No city today</li> : null}
            {g.items
              .sort((a, b) => b.temp - a.temp)
              .map((l) => (
                <li key={l.id} className="flex justify-between">
                  <Link href={`/destinations/${l.id}`} className="hover:underline">{l.name}</Link>
                  <span className="tabular-nums text-muted-foreground">{Math.round(l.temp)}°</span>
                </li>
              ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
