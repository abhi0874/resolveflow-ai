import Link from "next/link";
import { readPrivate, workspaceAccess } from "@/lib/workspace-access";
import type { UploadConfig } from "@/lib/documents";
import { AppShell } from "@/components/workspaces/app-shell";
import { KnowledgeList } from "./knowledge-list";
import { DocumentDetail } from "./document-detail";
export async function KnowledgePage({
  workspaceId,
  documentId,
}: {
  workspaceId?: string;
  documentId?: string;
}) {
  const access = await workspaceAccess();
  if (!access) return <Unavailable />;
  const { user, workspaces } = access;
  const selected = workspaceId
    ? workspaces.find((w) => w.id === workspaceId)
    : workspaces[0];
  if (!selected) return <Unavailable missing />;
  const configResponse = await readPrivate(
    `/workspaces/${selected.id}/documents/config`,
  );
  if (!configResponse) return <Unavailable />;
  const config: UploadConfig = await configResponse.json();
  return (
    <AppShell
      user={user}
      workspaces={workspaces}
      selected={selected}
      area="knowledge-base"
    >
      {documentId ? (
        <DocumentDetail
          key={selected.id + documentId}
          workspace={selected}
          documentId={documentId}
        />
      ) : (
        <KnowledgeList key={selected.id} workspace={selected} config={config} />
      )}
    </AppShell>
  );
}
function Unavailable({ missing = false }: { missing?: boolean }) {
  return (
    <main className="service-unavailable">
      <h1>
        {missing
          ? "Choose a workspace."
          : "Knowledge base temporarily unavailable."}
      </h1>
      <p>
        {missing
          ? "Select a workspace you belong to before opening its documents."
          : "Please refresh and try again shortly."}
      </p>
      <Link className="primary-link" href="/app">
        Go to workspaces
      </Link>
    </main>
  );
}
