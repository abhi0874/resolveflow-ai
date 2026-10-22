import Link from "next/link";
import { redirect } from "next/navigation";
import { serverGet } from "@/lib/server-api";
import type { User, Workspace } from "@/lib/session-api";
import type { UploadConfig } from "@/lib/documents";
import { AppShell } from "@/components/workspaces/app-shell";
import { KnowledgeList } from "./knowledge-list";
import { DocumentDetail } from "./document-detail";
async function read(path: string) {
  try {
    return await serverGet(path);
  } catch {
    return null;
  }
}
export async function KnowledgePage({
  workspaceId,
  documentId,
}: {
  workspaceId?: string;
  documentId?: string;
}) {
  const identity = await read("/auth/me");
  if (identity?.status === 401) redirect("/login");
  if (!identity?.ok) return <Unavailable />;
  const user: User = await identity.json();
  const response = await read("/workspaces");
  if (response?.status === 401) redirect("/login");
  if (!response?.ok) return <Unavailable />;
  const workspaces: Workspace[] = await response.json();
  const selected = workspaceId
    ? workspaces.find((w) => w.id === workspaceId)
    : workspaces[0];
  if (!selected) return <Unavailable missing />;
  const configResponse = await read(
    `/workspaces/${selected.id}/documents/config`,
  );
  if (configResponse?.status === 401) redirect("/login");
  if (!configResponse?.ok) return <Unavailable />;
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
