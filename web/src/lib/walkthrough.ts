/** Parses docs/08-walkthrough.md into steps: title, narrative, time budget (server only). */
import "server-only";
import { getDoc } from "@/lib/docs";

export type Step = { n: number; title: string; text: string; budget: string | null };

export async function walkthroughSteps(): Promise<Step[]> {
  const doc = await getDoc("08-walkthrough");
  if (!doc) return [];
  const items: string[] = [];
  for (const line of doc.body.split("\n")) {
    if (/^\d+\.\s/.test(line)) items.push(line);
    else if (items.length && /^\s{2,}\S/.test(line)) items[items.length - 1] += " " + line.trim();
  }
  return items.map((raw, i) => {
    const m = /^(\d+)\.\s+(?:\*\*(.+?)\*\*\s*)?(.*)$/.exec(raw);
    let text = (m?.[3] ?? raw).trim();
    const budget = /(\d+(?:\.\d+)?\s*(?:s|min))\.?$/.exec(text);
    if (budget) text = text.slice(0, budget.index).trim();
    return { n: i + 1, title: (m?.[2] ?? text).replace(/\.$/, ""), text: m?.[2] ? text : "", budget: budget?.[1] ?? null };
  });
}

/** The text of one H2 section of a document, without its heading. */
export async function docSection(slug: string, headingStart: string): Promise<string> {
  const doc = await getDoc(slug);
  if (!doc) return "";
  const lines = doc.body.split("\n");
  const start = lines.findIndex((l) => l.startsWith(`## ${headingStart}`));
  if (start < 0) return "";
  const end = lines.findIndex((l, i) => i > start && l.startsWith("## "));
  return lines.slice(start + 1, end < 0 ? undefined : end).join("\n");
}
