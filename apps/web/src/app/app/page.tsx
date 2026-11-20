import Link from "next/link";
import { readPrivate, workspaceAccess } from "@/lib/workspace-access";
import type { Member } from "@/lib/session-api";
import { WorkspacePanel } from "@/components/workspaces/workspace-panel";
export const dynamic = "force-dynamic";
export const metadata = {
  title: "Workspace · ResolveFlow AI",
  robots: { index: false, follow: false },
};

export default async function AppPage({
  searchParams,
}: {
  searchParams: Promise<{ workspace?: string }>;
}) {
  const access = await workspaceAccess();
  if (!access) return <Unavailable />;
  const { user, workspaces } = access;
  const query = await searchParams;
  const selected = query.workspace
    ? workspaces.find((item) => item.id === query.workspace)
    : workspaces[0];
  let members: Member[] = [];
  if (selected) {
    const response = await readPrivate(`/workspaces/${selected.id}/members`);
    if (!response) return <Unavailable />;
    members = await response.json();
  }
  return (
    <WorkspacePanel
      key={selected?.id ?? "empty"}
      user={user}
      workspaces={workspaces}
      selected={selected}
      initialMembers={members}
    />
  );
}

function Unavailable() {
  return (
    <main className="service-unavailable">
      <h1>We’ll be right back.</h1>
      <p>
        Your workspace is temporarily unavailable. Please try again shortly.
      </p>
      <Link href="/app" className="primary-link">
        Try again
      </Link>
    </main>
  );
}
