export function PageHeader({ eyebrow, title, lead }: { eyebrow: string; title: string; lead: string }) {
  return (
    <div className="mx-auto max-w-6xl px-4 pt-10 pb-6">
      <p className="label-mono text-muted-foreground">{eyebrow}</p>
      <h1 className="mt-2 text-3xl font-medium tracking-tight sm:text-4xl">{title}</h1>
      <p className="mt-3 max-w-2xl text-base text-muted-foreground">{lead}</p>
    </div>
  );
}
