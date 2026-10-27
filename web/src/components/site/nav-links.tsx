"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SECTIONS } from "@/lib/sections";
import { cn } from "@/lib/utils";

export function NavLinks() {
  const pathname = usePathname();
  return (
    <>
      {SECTIONS.map((s) => {
        const active = s.href === "/" ? pathname === "/" : pathname.startsWith(s.href);
        return (
          <Link
            key={s.href}
            href={s.href}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
              active ? "bg-accent text-accent-foreground font-medium" : "text-muted-foreground",
            )}
          >
            {s.label}
          </Link>
        );
      })}
    </>
  );
}
