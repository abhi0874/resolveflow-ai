import Link from "next/link";
import { readPrivate, workspaceAccess } from "@/lib/workspace-access";
import type { Member } from "@/lib/session-api";
import { AppShell } from "@/components/workspaces/app-shell";
import { TicketInbox } from "./ticket-inbox";
import { TicketDetail } from "./ticket-detail";

export async function TicketPage({
  workspaceId,
  ticketId,
}: {
  workspaceId?: string;
  ticketId?: string;
}) {
  const access = await workspaceAccess();
  if (!access) return <Unavailable />;
  const { user, workspaces } = access;
  const selected = workspaceId
    ? workspaces.find((w) => w.id === workspaceId)
    : workspaces[0];
  if (!selected) return <Unavailable missing />;
  const membersResponse = await readPrivate(
    `/workspaces/${selected.id}/tickets/assignees`,
  );
  if (!membersResponse) return <Unavailable />;
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
