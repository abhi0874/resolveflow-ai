"use client";
import { useRef, useState, type FormEvent } from "react";
import type { Member } from "@/lib/session-api";
import { priorities, statuses, ticketError, type Ticket } from "@/lib/tickets";
type Changes = {
  title: string;
  description: string;
  category: string | null;
  priority?: string;
  assigned_user_id?: string | null;
  status?: string;
  expected_version?: number;
};
export function TicketForm({
  ticket,
  manage,
  members,
  onSave,
  onCancel,
}: {
  ticket?: Ticket;
  manage: boolean;
  members: Member[];
  onSave: (values: Changes) => Promise<void>;
  onCancel: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    const data = new FormData(event.currentTarget);
    const title = String(data.get("title")).trim();
    if (!title) {
      setError("Enter a ticket title.");
      return;
    }
    const values: Changes = {
      title,
      description: String(data.get("description")),
      category: String(data.get("category")).trim() || null,
    };
    if (manage) {
      values.priority = String(data.get("priority"));
      values.assigned_user_id = String(data.get("assignee")) || null;
    }
    if (ticket) {
      values.status = String(data.get("status"));
      values.expected_version = ticket.version;
    }
    submitting.current = true;
    setPending(true);
    setError("");
    try {
      await onSave(values);
    } catch (e) {
      setError(ticketError(e));
      submitting.current = false;
      setPending(false);
    }
  }
  return (
    <form
      className="auth-form ticket-form"
      onSubmit={submit}
      aria-busy={pending}
    >
      <fieldset disabled={pending}>
        <div className="form-field">
          <label htmlFor="ticket-title">Ticket title</label>
          <input
            autoFocus
            id="ticket-title"
            name="title"
            required
            maxLength={200}
            defaultValue={ticket?.title}
            placeholder="A short summary of the issue"
          />
        </div>
        <div className="form-field">
          <label htmlFor="ticket-description">Description</label>
          <textarea
            id="ticket-description"
            name="description"
            rows={5}
            maxLength={8000}
            defaultValue={ticket?.description}
            placeholder="What happened? Include the context your team needs."
          />
        </div>
        <div className="ticket-field-grid">
          <div className="form-field">
            <label htmlFor="ticket-category">Category</label>
            <input
              id="ticket-category"
              name="category"
              maxLength={100}
              defaultValue={ticket?.category ?? ""}
              placeholder="e.g. Billing"
            />
          </div>
          {ticket && (
            <div className="form-field">
              <label htmlFor="ticket-status">Status</label>
              <select
                id="ticket-status"
                name="status"
                defaultValue={ticket.status}
              >
                {Object.entries(statuses).map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
          )}
          {manage && (
            <>
              <div className="form-field">
                <label htmlFor="ticket-priority">Priority</label>
                <select
                  id="ticket-priority"
                  name="priority"
                  defaultValue={ticket?.priority ?? "medium"}
                >
                  {Object.entries(priorities).map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="ticket-assignee">Assignee</label>
                <select
                  id="ticket-assignee"
                  name="assignee"
                  defaultValue={ticket?.assigned_user_id ?? ""}
                >
                  <option value="">Unassigned</option>
                  {members.map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.email}
                    </option>
                  ))}
                  {ticket?.assigned_user_id &&
                    !members.some(
                      (m) => m.user_id === ticket.assigned_user_id,
                    ) && (
                      <option value={ticket.assigned_user_id}>
                        Unavailable member — choose an eligible assignee
                      </option>
                    )}
                </select>
              </div>
            </>
          )}
        </div>
        {!manage && (
          <p className="field-help">
            Owners and admins manage priority and assignment. New tickets start
            at medium priority, unassigned.
          </p>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="ticket-actions">
          <button className="action-button" disabled={pending}>
            {pending ? "Saving…" : ticket ? "Save ticket" : "Create ticket"}
          </button>
          <button
            type="button"
            className="subtle-button"
            disabled={pending}
            onClick={onCancel}
          >
            Cancel
          </button>
        </div>
      </fieldset>
    </form>
  );
}
