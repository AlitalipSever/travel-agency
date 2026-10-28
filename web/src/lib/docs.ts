/**
 * The repository's documentation, read at build time (server only). `docs/` sits next to
 * `web/`; the Docker build copies it to the same relative place. A readable rewrite of a
 * document under `web/content/plain/` (same relative path) is preferred when it exists; the
 * source in `docs/` stays the reference. Results are cached with `use cache` so the pages
 * prerender to static HTML.
 */
import "server-only";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { cacheLife } from "next/cache";

const DOCS_DIR = path.resolve(process.cwd(), "../docs");
const PLAIN_DIR = path.resolve(process.cwd(), "content/plain");

export type Doc = {
  slug: string;
  title: string;
  status: string | null;
  headings: { id: string; text: string; level: number }[];
  body: string;
  /** True when the body comes from the readable version in `web/content/plain/`. */
  plain: boolean;
};

export type AdrSummary = { id: string; slug: string; title: string; status: string };

const DOC_SLUGS = [
  "00-domain",
  "01-requirements",
  "02-architecture",
  "03-data-model",
  "04-api",
  "05-work-packages",
  "06-operations",
  "07-roadmap",
  "08-walkthrough",
  "arc42-checklist",
  "plans/bookable",
] as const;

export function docSlugs(): string[] {
  return [...DOC_SLUGS];
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function headingsOf(body: string) {
  const out: Doc["headings"] = [];
  for (const line of body.split("\n")) {
    const m = /^(#{2,3})\s+(.*)$/.exec(line);
    if (m) out.push({ level: m[1].length, text: m[2].trim(), id: slugify(m[2]) });
  }
  return out;
}

function titleOf(body: string, fallback: string): string {
  const m = /^#\s+(.*)$/m.exec(body);
  return m ? m[1].trim() : fallback;
}

function statusOf(body: string): string | null {
  const m = /^Status:\s*(.*)$/m.exec(body);
  return m ? m[1].trim() : null;
}

/** The readable version when there is one, otherwise the source document. */
async function readSource(relative: string): Promise<{ body: string; plain: boolean }> {
  try {
    return { body: await readFile(path.join(PLAIN_DIR, relative), "utf8"), plain: true };
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
    return { body: await readFile(path.join(DOCS_DIR, relative), "utf8"), plain: false };
  }
}

async function readDoc(relative: string, slug: string): Promise<Doc> {
  const { body, plain } = await readSource(relative);
  return { slug, title: titleOf(body, slug), status: statusOf(body), headings: headingsOf(body), body, plain };
}

export async function getDoc(slug: string): Promise<Doc | null> {
  "use cache";
  cacheLife("max");
  if (!DOC_SLUGS.includes(slug as (typeof DOC_SLUGS)[number])) return null;
  return readDoc(`${slug}.md`, slug);
}

export async function listDocs(): Promise<Pick<Doc, "slug" | "title" | "status">[]> {
  "use cache";
  cacheLife("max");
  const docs = await Promise.all(DOC_SLUGS.map((s) => readDoc(`${s}.md`, s)));
  return docs.map(({ slug, title, status }) => ({ slug, title, status }));
}

async function adrFiles(): Promise<string[]> {
  const names = await readdir(path.join(DOCS_DIR, "adr"));
  return names.filter((n) => /^\d{4}-.*\.md$/.test(n) && !n.startsWith("0000")).sort();
}

export async function listAdrs(): Promise<AdrSummary[]> {
  "use cache";
  cacheLife("max");
  const files = await adrFiles();
  const out: AdrSummary[] = [];
  for (const file of files) {
    const { body } = await readSource(`adr/${file}`);
    const id = file.slice(0, 4);
    out.push({
      id,
      slug: file.replace(/\.md$/, ""),
      title: titleOf(body, file).replace(/^\d{4}\s+/, ""),
      status: statusOf(body) ?? "unknown",
    });
  }
  return out;
}

export async function getAdr(id: string): Promise<Doc | null> {
  "use cache";
  cacheLife("max");
  const file = (await adrFiles()).find((f) => f.startsWith(`${id}-`));
  if (!file) return null;
  const doc = await readDoc(`adr/${file}`, id);
  return { ...doc, title: doc.title.replace(/^\d{4}\s+/, "") };
}

/** Rewrite repository-relative markdown links to site routes. */
export function rewriteHref(href: string, from: "docs" | "adr"): string {
  if (/^(https?:)?\/\//.test(href) || href.startsWith("#")) return href;
  const [file, hash] = href.split("#");
  const suffix = hash ? `#${hash}` : "";
  let p = file.replace(/^\.\//, "");
  if (from === "adr") p = p.startsWith("../") ? p.slice(3) : p.startsWith("adr/") ? p : `adr/${p}`;
  const adr = /^(?:adr\/)?(\d{4})-.*\.md$/.exec(p);
  if (adr) return `/decisions/${adr[1]}${suffix}`;
  if (p === "adr/README.md" || p === "README.md" && from === "adr") return "/decisions";
  if (p === "README.md") return "/docs";
  const doc = /^(.*)\.md$/.exec(p);
  if (doc && DOC_SLUGS.includes(doc[1] as (typeof DOC_SLUGS)[number])) return `/docs/${doc[1]}${suffix}`;
  return href;
}
