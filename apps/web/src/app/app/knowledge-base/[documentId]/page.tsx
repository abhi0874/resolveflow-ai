import { KnowledgePage } from "@/components/knowledge/knowledge-page";
export const dynamic = "force-dynamic";
export const metadata = {
  title: "Document · ResolveFlow AI",
  robots: { index: false, follow: false },
};
export default async function Page({
  searchParams,
  params,
}: {
  searchParams: Promise<{ workspace?: string }>;
  params: Promise<{ documentId: string }>;
}) {
  return (
    <KnowledgePage
      workspaceId={(await searchParams).workspace}
      documentId={(await params).documentId}
    />
  );
}
