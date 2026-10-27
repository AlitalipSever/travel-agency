import type { Doc } from "@/lib/docs";
import { cn } from "@/lib/utils";

/** Section list from the document's H2 and H3 headings; sticky on wide screens. */
export function Toc({ headings }: { headings: Doc["headings"] }) {
  const items = headings.filter((h) => h.level === 2);
  if (items.length < 2) return null;
  return (
    <aside className="hidden lg:block">
      <nav className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto border-l pl-4 text-sm">
        <p className="label-mono mb-2 text-muted-foreground">Sections</p>
        <ul className="space-y-1">
          {items.map((h) => (
            <li key={h.id}>
              <a href={`#${h.id}`} className={cn("block py-0.5 text-muted-foreground hover:text-foreground")}>
                {h.text}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
