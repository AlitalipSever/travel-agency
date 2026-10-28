import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/site/page-header";
import { Markdown } from "@/components/docs/markdown";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getDoc } from "@/lib/docs";

export const metadata: Metadata = { title: "Plan" };

const PROSE = "prose prose-neutral dark:prose-invert max-w-none prose-headings:scroll-mt-20 prose-headings:font-medium prose-headings:tracking-tight prose-a:text-spectral-sky prose-code:before:content-none prose-code:after:content-none prose-pre:bg-muted prose-pre:text-foreground";

export default async function PlanPage() {
  const [packages, roadmap] = await Promise.all([getDoc("05-work-packages"), getDoc("07-roadmap")]);
  return (
    <>
      <PageHeader
        eyebrow="Plan"
        title="Work packages and roadmap"
        lead="The work cut as it would be for a team of three in two tracks, what is done with its pull request, what was deliberately left out, and the next two weeks. The requirements and the domain the plan serves are one click away."
      />
      <div className="mx-auto max-w-6xl px-4 pb-20">
        <div className="mb-6 flex flex-wrap gap-x-4 gap-y-1 text-sm">
          <Link href="/docs/01-requirements" className="text-spectral-sky hover:underline">01 Requirements and acceptance checks</Link>
          <Link href="/docs/00-domain" className="text-spectral-sky hover:underline">00 Domain: stakeholders, actors, language</Link>
          <Link href="/docs/02-architecture" className="text-spectral-sky hover:underline">02 Architecture (arc42)</Link>
        </div>
        <Tabs defaultValue="packages">
          <TabsList>
            <TabsTrigger value="packages">Work packages</TabsTrigger>
            <TabsTrigger value="roadmap">Roadmap</TabsTrigger>
          </TabsList>
          <TabsContent value="packages">
            <div className={`${PROSE} mt-6`}>{packages ? <Markdown body={packages.body} from="docs" /> : null}</div>
          </TabsContent>
          <TabsContent value="roadmap">
            <div className={`${PROSE} mt-6`}>{roadmap ? <Markdown body={roadmap.body} from="docs" /> : null}</div>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
