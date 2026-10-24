import Link from "next/link";
import { redirect } from "next/navigation";
import { serverGet } from "@/lib/server-api";
import type { User, Workspace, Member } from "@/lib/session-api";
import { WorkspacePanel } from "@/components/workspaces/workspace-panel";
export const dynamic = "force-dynamic";
export const metadata = {
  title: "Workspace · ResolveFlow AI",
  robots: { index: false, follow: false },
};

async function read(path: string): Promise<Response | null> {
  try {
    return await serverGet(path);
  } catch {
    return null;
  }
}

export default async function AppPage({
  searchParams,
}: {
  searchParams: Promise<{ workspace?: string }>;
}) {
  const identity = await read("/auth/me");
  if (identity?.status === 401) redirect("/login");
  if (!identity?.ok) return <Unavailable />;
  const user: User = await identity.json();
  const response = await read("/workspaces");
  if (response?.status === 401) redirect("/login");
  if (response?.status === 403) {
    const failure = await response.clone().json().catch(() => null);
    if (failure?.error?.code === "email_verification_required") redirect("/verification-required");
  }
  if (!response?.ok) return <Unavailable />;
  const workspaces: Workspace[] = await response.json();
  const query = await searchParams;
  const selected = query.workspace
    ? workspaces.find((item) => item.id === query.workspace)
    : workspaces[0];
  let members: Member[] = [];
  if (selected) {
    const response = await read(`/workspaces/${selected.id}/members`);
    if (response?.status === 401) redirect("/login");
    if (!response?.ok) return <Unavailable />;
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
      <Link href="/" className="back-link">
        Back to home
      </Link>
    </main>
  );
}
