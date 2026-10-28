"use client";

import Link from "next/link";
import { BookOpen, ChevronDown } from "lucide-react";
import { SECTIONS } from "@/lib/sections";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/** Everything about how the site is built, behind one menu so the agency pages stay clean. */
export function CaseStudyMenu() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" size="sm" />}>
        <BookOpen className="size-4" />
        <span className="hidden sm:inline">Case study</span>
        <ChevronDown className="size-3.5 opacity-70" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuGroup>
          <DropdownMenuLabel>How this site is built</DropdownMenuLabel>
          {SECTIONS.map((s) => (
          <DropdownMenuItem key={s.href} render={<Link href={s.href} />}>
            <div>
              <div className="text-sm">{s.label}</div>
              <div className="text-xs text-muted-foreground">{s.short}</div>
            </div>
          </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem render={<a href="/api/docs-link" />}>Swagger UI (the API)</DropdownMenuItem>
        <DropdownMenuItem render={<Link href="/docs" />}>Documents (arc42, ADRs)</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
