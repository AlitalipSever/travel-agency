import type { ReactElement, ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import { Mermaid } from "@/components/docs/mermaid";
import { rewriteHref } from "@/lib/docs";

type PreProps = { children?: ReactNode };

function codeOf(children: ReactNode): { lang: string | null; text: string } | null {
  const el = children as ReactElement<{ className?: string; children?: ReactNode }> | undefined;
  if (!el || typeof el !== "object" || !("props" in el)) return null;
  const lang = /language-(\w+)/.exec(el.props.className ?? "")?.[1] ?? null;
  const text = String(el.props.children ?? "");
  return { lang, text };
}

/** Repository markdown rendered on the server; Mermaid blocks become client components. */
export function Markdown({ body, from }: { body: string; from: "docs" | "adr" }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeSlug]}
      components={{
        h1: () => null,
        a: ({ href, children }) => <a href={rewriteHref(href ?? "", from)}>{children}</a>,
        pre: ({ children }: PreProps) => {
          const code = codeOf(children);
          if (code?.lang === "mermaid") return <Mermaid chart={code.text} />;
          return <pre>{children}</pre>;
        },
        table: ({ children }) => (
          <div className="not-prose my-6 overflow-x-auto rounded-md border">
            <table className="w-full text-sm">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-muted text-left label-mono text-muted-foreground">{children}</thead>,
        th: ({ children }) => <th className="px-3 py-2 font-normal align-top">{children}</th>,
        td: ({ children }) => <td className="border-t px-3 py-2 align-top">{children}</td>,
      }}
    >
      {body}
    </ReactMarkdown>
  );
}
