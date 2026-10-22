"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api, type Workspace, type Member } from "@/lib/session-api";
import {
  dateLabel,
  priorities,
  statuses,
  ticketError,
  type Ticket,
  type ResultPage,
} from "@/lib/tickets";
import { TicketForm } from "./ticket-form";
export function TicketInbox({
  workspace,
  members,
}: {
  workspace: Workspace;
  members: Member[];
}) {
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [query, setQuery] = useState("page=1&page_size=25");
  const [result, setResult] = useState<ResultPage<Ticket> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const base = `/workspaces/${workspace.id}/tickets`;
  const write = workspace.permissions.includes("ticket:write");
  const manage = workspace.permissions.includes("ticket:manage");
  useEffect(() => {
    let current = true;
    api<ResultPage<Ticket>>(`${base}?${query}`)
      .then((data) => {
        if (current) {
          setResult(data);
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
  }, [base, query, revision]);
  function filter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = new URLSearchParams({ page: "1", page_size: "25" });
    for (const [key, value] of new FormData(event.currentTarget))
      if (String(value).trim()) next.set(key, String(value).trim());
    setLoading(true);
    setQuery(next.toString());
    setRevision((v) => v + 1);
  }
  function page(number: number) {
    const next = new URLSearchParams(query);
    next.set("page", String(number));
    setLoading(true);
    setQuery(next.toString());
  }
  return (
    <>
      <header className="workspace-heading">
        <div>
          <span className="eyebrow">{workspace.name} / SUPPORT</span>
          <h1>Your ticket inbox.</h1>
          <p>
            A clear view of what needs attention. A shared place to move it
            forward.
          </p>
        </div>
        {write && !creating && (
          <button className="action-button" onClick={() => setCreating(true)}>
            ＋ Create ticket
          </button>
        )}
      </header>
      {creating ? (
        <section className="workspace-card">
          <span className="eyebrow">NEW REQUEST</span>
          <h2>Create a ticket</h2>
          <TicketForm
            manage={manage}
            members={members}
            onCancel={() => setCreating(false)}
            onSave={async (values) => {
              const created = await api<Ticket>(base, "POST", values);
              router.push(
                `/app/tickets/${created.id}?workspace=${workspace.id}`,
              );
            }}
          />
        </section>
      ) : (
        <>
          <section className="ticket-toolbar" aria-label="Ticket filters">
            <form onSubmit={filter}>
              <div className="ticket-search-row">
                <div className="form-field">
                  <label htmlFor="ticket-search">Search tickets</label>
                  <input
                    id="ticket-search"
                    name="search"
                    maxLength={200}
                    placeholder="Search titles and descriptions…"
                  />
                </div>
                <button className="action-button">Apply filters</button>
              </div>
              <div className="ticket-filters">
                <Filter name="status" label="Status" options={statuses} />
                <Filter name="priority" label="Priority" options={priorities} />
                <div className="form-field">
                  <label htmlFor="filter-assignee">Assignee</label>
                  <select id="filter-assignee" name="assignee">
                    <option value="">Everyone</option>
                    <option value="unassigned">Unassigned</option>
                    {members.map((m) => (
                      <option key={m.user_id} value={m.user_id}>
                        {m.email}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="filter-category">Category</label>
                  <input
                    id="filter-category"
                    name="category"
                    maxLength={100}
                    placeholder="All categories"
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="filter-sort">Sort by</label>
                  <select id="filter-sort" name="sort">
                    <option value="created_at">Created</option>
                    <option value="updated_at">Last updated</option>
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="filter-direction">Order</label>
                  <select id="filter-direction" name="direction">
                    <option value="desc">Newest first</option>
                    <option value="asc">Oldest first</option>
                  </select>
                </div>
              </div>
              <button
                type="reset"
                className="subtle-button"
                onClick={() => {
                  setLoading(true);
                  setQuery("page=1&page_size=25");
                  setRevision((v) => v + 1);
                }}
              >
                Clear filters
              </button>
            </form>
          </section>
          <section
            className="ticket-list workspace-card"
            aria-label="Ticket results"
            aria-busy={loading}
          >
            <div className="card-heading">
              <h2>All tickets</h2>
              <span className="role-badge">
                {loading ? "Loading…" : `${result?.total ?? 0} results`}
              </span>
            </div>
            {error ? (
              <div className="ticket-empty">
                <p className="form-error" role="alert">
                  {error}
                </p>
                <button
                  className="subtle-button"
                  onClick={() => {
                    setLoading(true);
                    setRevision((v) => v + 1);
                  }}
                >
                  Try again
                </button>
              </div>
            ) : loading ? (
              <div role="status" aria-label="Loading tickets">
                {[1, 2, 3, 4].map((i) => (
                  <div className="ticket-skeleton" key={i} />
                ))}
              </div>
            ) : result?.items.length ? (
              <>
                <div className="ticket-table-scroll">
                  <table className="ticket-table">
                    <caption className="sr-only">
                      Tickets in {workspace.name}
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Ticket</th>
                        <th scope="col">Status</th>
                        <th scope="col">Priority</th>
                        <th scope="col">Assignee</th>
                        <th scope="col">Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.items.map((ticket) => (
                        <tr key={ticket.id}>
                          <td>
                            <Link
                              className="ticket-title-link"
                              href={`/app/tickets/${ticket.id}?workspace=${workspace.id}`}
                            >
                              {ticket.title}
                            </Link>
                            <small>
                              {ticket.category ?? "Uncategorized"} ·{" "}
                              {ticket.id.slice(0, 8)}
                            </small>
                          </td>
                          <td>
                            <TicketBadge value={ticket.status}>
                              {statuses[ticket.status]}
                            </TicketBadge>
                          </td>
                          <td>
                            <TicketBadge value={ticket.priority}>
                              {priorities[ticket.priority]}
                            </TicketBadge>
                          </td>
                          <td>
                            {members.find(
                              (m) => m.user_id === ticket.assigned_user_id,
                            )?.email ??
                              (ticket.assigned_user_id
                                ? "Unavailable member"
                                : "Unassigned")}
                          </td>
                          <td>
                            <time dateTime={ticket.updated_at}>
                              {dateLabel(ticket.updated_at)}
                            </time>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="ticket-pagination">
                  <span>
                    Page {result.page} of {result.pages} · {result.total}{" "}
                    tickets
                  </span>
                  <div>
                    <button
                      className="subtle-button"
                      disabled={result.page <= 1}
                      onClick={() => page(result.page - 1)}
                    >
                      ← Previous
                    </button>
                    <button
                      className="subtle-button"
                      disabled={result.page >= result.pages}
                      onClick={() => page(result.page + 1)}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="ticket-empty">
                <span className="empty-symbol" aria-hidden="true">
                  ◫
                </span>
                <h3>No tickets here yet.</h3>
                <p>
                  Create a ticket to get started, or clear your filters to see
                  more results.
                </p>
              </div>
            )}
          </section>
          {!write && (
            <p className="field-help">
              You have read-only access. Ask an owner or admin for support
              access.
            </p>
          )}
        </>
      )}
    </>
  );
}
function Filter({
  name,
  label,
  options,
}: {
  name: string;
  label: string;
  options: Record<string, string>;
}) {
  return (
    <div className="form-field">
      <label htmlFor={`filter-${name}`}>{label}</label>
      <select id={`filter-${name}`} name={name}>
        <option value="">Any {label.toLowerCase()}</option>
        {Object.entries(options).map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </div>
  );
}
export function TicketBadge({
  value,
  children,
}: {
  value: string;
  children: React.ReactNode;
}) {
  return (
    <span className={`ticket-badge ticket-badge-${value}`}>
      <span aria-hidden="true">●</span> {children}
    </span>
  );
}
