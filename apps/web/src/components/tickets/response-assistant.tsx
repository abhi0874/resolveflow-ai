"use client";
import { DraftCard } from "./draft-card";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/session-api";
import { dateLabel, type ResultPage, type Ticket } from "@/lib/tickets";
import { draftError, draftFailure, draftStates, type Draft, type DraftConfig } from "@/lib/drafts";

export function ResponseAssistant({ base, workspaceId, ticket, editable }: {
  base: string; workspaceId: string; ticket: Ticket; editable: boolean;
}) {
  const [config, setConfig] = useState<DraftConfig | null>(null);
  const [history, setHistory] = useState<ResultPage<Draft> | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const busy = useRef(false);
  const requestId = useRef<string | null>(null);
  useEffect(() => {
    let current = true;
    Promise.all([
      api<DraftConfig>(base + "/response-config"),
      api<ResultPage<Draft>>(`${base}/drafts?page=${page}&page_size=5`),
    ]).then(([configuration, drafts]) => {
      if (current) { setConfig(configuration); setHistory(drafts); }
    }).catch(e => { if (current) { setError(draftError(e)); setHistory(null); } })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [base, page, refresh]);
  const draft = history?.items.find(d => d.id === selected) ?? history?.items[0];
  function reload() { setLoading(true); setRefresh(v => v + 1); }
  async function generate() {
    if (busy.current) return;
    busy.current = true; setPending(true); setError("");
    requestId.current ??= crypto.randomUUID();
    try {
      const result = await api<Draft>(base + "/generate-response", "POST", {
        request_id: requestId.current, expected_ticket_version: ticket.version,
        synthetic_confirmed: confirmed,
      });
      requestId.current = null;
      setSelected(result.id); setPage(1);
      if (result.generation_status === "failed") setError(draftFailure(result.error_code));
      reload();
    } catch (e) {
      // Keep the same key for uncertain transport failures; replay cannot spend quota twice.
      if (e instanceof ApiError && e.code) requestId.current = null;
      setError(draftError(e)); reload();
    } finally { busy.current = false; setPending(false); }
  }
  async function review(action: "approved" | "rejected" | "needs_revision") {
    if (!draft || busy.current) return;
    busy.current = true; setPending(true); setError("");
    try {
      await api<Draft>(`${base}/drafts/${draft.id}/review`, "POST", {
        expected_version: draft.version, action,
      });
      reload();
    } catch (e) { setError(draftError(e)); reload(); }
    finally { busy.current = false; setPending(false); }
  }
  return <section className="workspace-card response-assistant" aria-label="Response assistant" aria-busy={pending || loading}>
    <div className="card-heading">
      <div><span className="eyebrow">EVIDENCE & HUMAN REVIEW</span><h2>Response assistant</h2></div>
      <button className="subtle-button" disabled={pending || loading} onClick={reload}>Refresh drafts</button>
    </div>
    <p className="field-help">Create a draft from this ticket and indexed knowledge. Review every claim and source. Approval records an internal decision; nothing is sent to the customer.</p>
    {config?.fixture && <p className="role-badge">Deterministic test fixture · not Gemini inference</p>}
    {config && !config.available && <p className="field-help">Live Gemini is not configured for this workspace. Evidence checks can still return an abstention.</p>}
    {config?.available && config.synthetic_confirmation_required && editable && <label className="draft-confirmation">
      <input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} disabled={pending} />
      I confirm this ticket and its knowledge base contain only synthetic data. Selected text will be sent to Google’s free-tier API.
    </label>}
    {editable && <button className="action-button" disabled={pending || loading || (!!config?.available && config.synthetic_confirmation_required && !confirmed)}
      onClick={() => void generate()}>{pending ? "Working…" : "Generate response draft"}</button>}
    {pending && <p role="status">Processing your draft request…</p>}
    {error && <p role="alert" className="form-error">{error}</p>}
    {loading && <p role="status">Loading draft history…</p>}
    {!loading && history?.total === 0 && <p>No drafts yet. Index relevant documents in the knowledge base, then generate a response.</p>}
    {!!history?.items.length && <>
      <label className="draft-history-label">Draft history
        <select value={draft?.id ?? ""} disabled={pending || loading} onChange={e => setSelected(e.target.value)}>
          {history.items.map(d => <option key={d.id} value={d.id}>{dateLabel(d.created_at)} · {d.id.slice(0,8)} · {d.generation_status === "completed" ? draftStates[d.review_status] : d.generation_status}</option>)}
        </select>
      </label>
      {history.pages > 1 && <div className="ticket-actions">
        <button className="subtle-button" disabled={page === 1 || loading || pending} onClick={() => { setLoading(true); setPage(v => v - 1); }}>Newer drafts</button>
        <span>Page {page} of {history.pages}</span>
        <button className="subtle-button" disabled={page === history.pages || loading || pending} onClick={() => { setLoading(true); setPage(v => v + 1); }}>Older drafts</button>
      </div>}
    </>}
    {draft && <DraftCard draft={draft} workspaceId={workspaceId} editable={editable}
      pending={pending} loading={loading} review={review} />}
  </section>;
}
