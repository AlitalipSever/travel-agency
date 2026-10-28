"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AGENCY_NAV } from "@/lib/agency";
import { cn } from "@/lib/utils";

export function NavLinks({ onNavigate }: { onNavigate?: () => void } = {}) {
  const pathname = usePathname();
  return (
    <>
      {AGENCY_NAV.map((s) => {
        const active = s.href === "/" ? pathname === "/" : pathname.startsWith(s.href);
        return (
          <Link
            key={s.href}
            href={s.href}
            onClick={onNavigate}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-accent hover:text-accent-foreground",
              active ? "text-foreground font-medium" : "text-muted-foreground",
            )}
          >
            {s.label}
          </Link>
        );
      })}
    </>
  );
}
