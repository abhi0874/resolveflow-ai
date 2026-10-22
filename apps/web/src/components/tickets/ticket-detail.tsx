"use client";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, type Member, type User, type Workspace } from "@/lib/session-api";
import {
  dateLabel,
  priorities,
  statuses,
  ticketError,
  type Ticket,
  type TicketNote,
  type Activity,
  type ResultPage,
} from "@/lib/tickets";
import { TicketForm } from "./ticket-form";
import { TicketClassification } from "./ticket-classification";
import { WorkflowPanel } from "./workflow-panel";
import { ResponseAssistant } from "./response-assistant";
import { TicketBadge } from "./ticket-inbox";
export function TicketDetail({
  workspace,
  user,
  ticketId,
  members,
}: {
  workspace: Workspace;
  user: User;
  ticketId: string;
  members: Member[];
}) {
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState(false);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const base = `/workspaces/${workspace.id}/tickets/${encodeURIComponent(ticketId)}`;
  useEffect(() => {
    let current = true;
    api<Ticket>(base)
      .then((data) => {
        if (current) {
          setTicket(data);
          setError("");
        }
      })
      .catch((e) => {
        if (current) {
          setError(ticketError(e));
          setTicket(null);
        }
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [base, revision]);
  const manage = workspace.permissions.includes("ticket:manage");
  const write = workspace.permissions.includes("ticket:write");
  const edit =
    write &&
    (manage ||
      !ticket?.assigned_user_id ||
      ticket.assigned_user_id === user.id);
  function refresh() {
    setEditing(false);
    setLoading(true);
    setRevision((v) => v + 1);
  }
  return (
    <>
      <Link
        className="back-link"
        href={`/app/tickets?workspace=${workspace.id}`}
      >
        ← Ticket inbox
      </Link>
      {error && (
        <div className="workspace-card">
          <p role="alert" className="form-error">
            {error}
          </p>
          <button className="subtle-button" onClick={refresh}>
            Refresh ticket
          </button>
        </div>
      )}
      {loading ? (
        <div role="status" aria-label="Loading ticket">
          {[1, 2, 3].map((i) => (
            <div className="ticket-skeleton" key={i} />
          ))}
        </div>
      ) : (
        ticket && (
          <>
            <header className="workspace-heading ticket-detail-heading">
              <div>
                <span className="eyebrow">
                  TICKET / {ticket.id.slice(0, 8)}
                </span>
                <h1>{ticket.title}</h1>
                <div className="ticket-actions">
                  <TicketBadge value={ticket.status}>
                    {statuses[ticket.status]}
                  </TicketBadge>
                  <TicketBadge value={ticket.priority}>
                    {priorities[ticket.priority]}
                  </TicketBadge>
                </div>
              </div>
              <div className="ticket-actions">
                {edit && !editing && (
                  <button
                    className="action-button"
                    onClick={() => {
                      setEditing(true);
                      setNotice("");
                    }}
                  >
                    Edit ticket
                  </button>
                )}
                <button className="subtle-button" onClick={refresh}>
                  Refresh ticket
                </button>
              </div>
            </header>
            {notice && (
              <p className="success-message" role="status">
                {notice}
              </p>
            )}
            {editing ? (
              <section className="workspace-card">
                <h2>Edit ticket</h2>
                <TicketForm
                  key={ticket.version}
                  ticket={ticket}
                  manage={manage}
                  members={members}
                  onCancel={() => setEditing(false)}
                  onSave={async (values) => {
                    const saved = await api<Ticket>(base, "PATCH", values);
                    setTicket(saved);
                    setEditing(false);
                    setNotice("Ticket saved.");
                    setRevision((v) => v + 1);
                  }}
                />
              </section>
            ) : (
              <div className="ticket-detail-grid">
                <section className="workspace-card">
                  <span className="eyebrow">THE REQUEST</span>
                  <h2>Description</h2>
                  <p className="ticket-prose">
                    {ticket.description || "No description provided."}
                  </p>
                </section>
                <section className="workspace-card ticket-properties">
                  <h2>Details</h2>
                  <dl>
                    <dt>Assignee</dt>
                    <dd>
                      {members.find(
                        (m) => m.user_id === ticket.assigned_user_id,
                      )?.email ??
                        (ticket.assigned_user_id
                          ? "Unavailable member"
                          : "Unassigned")}
                    </dd>
                    <dt>Category</dt>
                    <dd>{ticket.category ?? "Uncategorized"}</dd>
                    <dt>Created</dt>
                    <dd>
                      <time dateTime={ticket.created_at}>
                        {dateLabel(ticket.created_at)}
                      </time>
                    </dd>
                    <dt>Last updated</dt>
                    <dd>
                      <time dateTime={ticket.updated_at}>
                        {dateLabel(ticket.updated_at)}
                      </time>
                    </dd>
                  </dl>
                </section>
              </div>
            )}
            {edit && !editing && (
              <TicketClassification
                key={`${ticket.id}-${ticket.version}`}
                base={base}
                ticket={ticket}
                onAccepted={(saved) => {
                  setTicket(saved);
                  setNotice("Suggested category applied. Ticket activity updated.");
                  setRevision((v) => v + 1);
                }}
              />
            )}
            {workspace.permissions.includes("document:content") && !editing && (
              <div className="ticket-ai-sections">
                <WorkflowPanel key={`workflow-${ticket.id}-${ticket.version}`} base={base}
                  workspaceId={workspace.id} ticket={ticket} editable={edit} />
              <ResponseAssistant key={`${ticket.id}-${ticket.version}`} base={base}
                workspaceId={workspace.id} ticket={ticket} editable={edit} />
              </div>
            )}
            {!edit && (
              <p className="field-help">
                {write
                  ? "You can edit unassigned tickets or tickets assigned to you. You can still add internal context below."
                  : "Your role can read this ticket. Editing and notes require support access."}
              </p>
            )}
            <div className="ticket-detail-grid ticket-conversation">
              <section className="workspace-card">
                <span className="eyebrow">TEAM ONLY</span>
                <h2>Internal notes</h2>
                <p className="field-help">
                  Shared with workspace members. Nothing here is sent to a
                  customer.
                </p>
                {write && (
                  <NoteForm
                    base={base}
                    onAdded={() => {
                      setRevision((v) => v + 1);
                      setNotice("Internal note added.");
                    }}
                  />
                )}
                <History<TicketNote>
                  key={`notes-${revision}`}
                  base={base + "/notes"}
                  label="notes"
                  render={(note) => (
                    <>
                      <div className="history-byline">
                        <strong>{note.author_email}</strong>
                        <time dateTime={note.created_at}>
                          {dateLabel(note.created_at)}
                        </time>
                      </div>
                      <p className="ticket-prose">{note.body}</p>
                    </>
                  )}
                />
              </section>
              <section className="workspace-card">
                <span className="eyebrow">AUDIT TRAIL</span>
                <h2>Activity</h2>
                <History<Activity>
                  key={`activity-${revision}`}
                  base={base + "/activities"}
                  label="activity"
                  render={(event) => (
                    <>
                      <p>{activityLabel(event, members)}</p>
                      <div className="history-byline">
                        <span>{event.actor_email}</span>
                        <time dateTime={event.created_at}>
                          {dateLabel(event.created_at)}
                        </time>
                      </div>
                    </>
                  )}
                />
              </section>
            </div>
          </>
        )
      )}
    </>
  );
}
function NoteForm({ base, onAdded }: { base: string; onAdded: () => void }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const sending = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current) return;
    const form = event.currentTarget;
    const body = String(new FormData(form).get("body")).trim();
    if (!body) {
      setError("Enter a note before saving.");
      return;
    }
    sending.current = true;
    setPending(true);
    setError("");
    try {
      await api(base + "/notes", "POST", { body });
      form.reset();
      onAdded();
    } catch (e) {
      setError(ticketError(e));
    } finally {
      sending.current = false;
      setPending(false);
    }
  }
  return (
    <form className="auth-form note-form" onSubmit={submit} aria-busy={pending}>
      <div className="form-field">
        <label htmlFor="internal-note">Add internal note</label>
        <textarea
          id="internal-note"
          name="body"
          rows={3}
          maxLength={4000}
          required
          disabled={pending}
          placeholder="Add context for your team…"
        />
      </div>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      <button className="action-button" disabled={pending}>
        {pending ? "Adding…" : "Add note"}
      </button>
    </form>
  );
}
function History<T extends { id: string }>({
  base,
  label,
  render,
}: {
  base: string;
  label: string;
  render: (item: T) => React.ReactNode;
}) {
  const [result, setResult] = useState<ResultPage<T> | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let current = true;
    api<ResultPage<T>>(`${base}?page=${page}&page_size=10`)
      .then((value) => {
        if (current) {
          setResult(value);
          setError("");
        }
      })
      .catch((e) => {
        if (current) setError(ticketError(e));
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [base, page, retry]);
  return (
    <div aria-busy={loading}>
      {error ? (
        <>
          <p role="alert" className="form-error">
            {error}
          </p>
          <button
            className="subtle-button"
            onClick={() => {
              setLoading(true);
              setRetry((v) => v + 1);
            }}
          >
            Retry {label}
          </button>
        </>
      ) : loading ? (
        <p role="status">Loading {label}…</p>
      ) : (
        <>
          <ol className="ticket-history" aria-label={label}>
            {result?.items.map((item) => (
              <li key={item.id}>{render(item)}</li>
            ))}
          </ol>
          {!result?.items.length && (
            <p className="field-help">No {label} yet.</p>
          )}
          {result && result.pages > 1 && (
            <div className="ticket-pagination">
              <span>
                {result.page} / {result.pages}
              </span>
              <button
                className="subtle-button"
                disabled={page <= 1}
                onClick={() => {
                  setLoading(true);
                  setPage((v) => v - 1);
                }}
              >
                Newer {label}
              </button>
              <button
                className="subtle-button"
                disabled={page >= result.pages}
                onClick={() => {
                  setLoading(true);
                  setPage((v) => v + 1);
                }}
              >
                Older {label}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
function activityLabel(event: Activity, members: Member[]) {
  const from =
    typeof event.details.from === "string" ? event.details.from : null;
  const to = typeof event.details.to === "string" ? event.details.to : null;
  if (event.action === "created") return "Ticket created";
  if (event.action === "note_added") return "Internal note added";
  if (event.action === "updated")
    return `Updated ${Array.isArray(event.details.fields) ? event.details.fields.join(", ") : "ticket details"}`;
  if (event.action === "assignment_changed") {
    const name = (id: string | null) =>
      id
        ? (members.find((m) => m.user_id === id)?.email ??
          "former or unavailable member")
        : "unassigned";
    return `Assignment: ${name(from)} → ${name(to)}${event.details.reason ? " (membership changed)" : ""}`;
  }
  const labels: Record<string, string> = { ...statuses, ...priorities };
  return `${event.action === "status_changed" ? "Status" : "Priority"}: ${labels[from ?? ""] ?? from} → ${labels[to ?? ""] ?? to}`;
}
