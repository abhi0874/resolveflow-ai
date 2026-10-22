import Link from "next/link";
import { redirect } from "next/navigation";
import { serverGet } from "@/lib/server-api";
import type { User, Workspace, Member } from "@/lib/session-api";
import { AppShell } from "@/components/workspaces/app-shell";
import { TicketInbox } from "./ticket-inbox";
import { TicketDetail } from "./ticket-detail";

async function read(path: string) {
  try {
    return await serverGet(path);
  } catch {
    return null;
  }
}
export async function TicketPage({
  workspaceId,
  ticketId,
}: {
  workspaceId?: string;
  ticketId?: string;
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
  const membersResponse = await read(
    `/workspaces/${selected.id}/tickets/assignees`,
  );
  if (membersResponse?.status === 401) redirect("/login");
  if (!membersResponse?.ok) return <Unavailable />;
  const members: Member[] = await membersResponse.json();
  return (
    <AppShell user={user} workspaces={workspaces} selected={selected}>
      {ticketId ? (
        <TicketDetail
          key={selected.id + ticketId}
          workspace={selected}
          user={user}
          ticketId={ticketId}
          members={members}
        />
      ) : (
        <TicketInbox key={selected.id} workspace={selected} members={members} />
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
          : "Tickets are temporarily unavailable."}
      </h1>
      <p>
        {missing
          ? "Open a workspace you belong to, or create one to start managing tickets."
          : "Please refresh the page and try again."}
      </p>
      <Link className="primary-link" href="/app">
        Go to workspaces
      </Link>
    </main>
  );
}
