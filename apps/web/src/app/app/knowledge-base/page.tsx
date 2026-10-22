import { KnowledgePage } from "@/components/knowledge/knowledge-page";
export const dynamic = "force-dynamic";
export const metadata = {
  title: "Knowledge base · ResolveFlow AI",
  robots: { index: false, follow: false },
};
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ workspace?: string }>;
}) {
  return <KnowledgePage workspaceId={(await searchParams).workspace} />;
}
