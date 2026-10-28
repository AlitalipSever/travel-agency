/** Route-level loading state: a quiet frame while the API answers. */
export function PageSkeleton({ hero = false }: { hero?: boolean }) {
  return (
    <div>
      {hero ? <div className="h-72 animate-pulse bg-muted sm:h-96" /> : null}
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="h-9 w-64 animate-pulse rounded bg-muted" />
        <div className="mt-3 h-5 w-96 max-w-full animate-pulse rounded bg-muted" />
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => <div key={i} className="h-64 animate-pulse rounded-xl border bg-muted/60" />)}
        </div>
      </div>
    </div>
  );
}
