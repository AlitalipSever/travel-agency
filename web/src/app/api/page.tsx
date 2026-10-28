import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader } from "@/components/site/page-header";
import { SchemaBrowser } from "@/components/api/schema-browser";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "API" };

export default function ApiPage() {
  return (
    <>
      <PageHeader
        eyebrow="API"
        title="The API contract"
        lead="Generated from the code (drf-spectacular) and read live when you open this page. Every call needs a token header; errors follow RFC 7807 problem details."
      />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <div className="mb-6 flex flex-wrap gap-2">
          <Button nativeButton={false} render={<a href="/api/docs-link" />}>Open Swagger UI</Button>
          <Button variant="outline" nativeButton={false} render={<Link href="/docs/04-api" />}>Read 04-api: conventions, shapes, roles</Button>
        </div>
        <Suspense fallback={<Skeleton className="h-96 w-full" />}>
          <SchemaBrowser />
        </Suspense>
      </div>
    </>
  );
}
