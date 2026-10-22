"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/session-api";
import { dateLabel, type ResultPage, type Ticket } from "@/lib/tickets";
import { type Draft, type DraftConfig } from "@/lib/drafts";
import { workflowError, workflowFailure, workflowLabel, type Workflow } from "@/lib/workflows";
import { WorkflowStages } from "./workflow-stages";
import { DraftCard } from "./draft-card";

export function WorkflowPanel({ base, workspaceId, ticket, editable }: {
  base: string; workspaceId: string; ticket: Ticket; editable: boolean;
}) {
  const [history, setHistory] = useState<ResultPage<Workflow> | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [config, setConfig] = useState<DraftConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [page, setPage] = useState(1);
  const [refresh, setRefresh] = useState(0);
  const [pollExpired, setPollExpired] = useState(false);
  const busy = useRef(false);
  const requestId = useRef<string | null>(null);
  const run = history?.items.find(item => item.id === selected) ?? history?.items[0];
  const location = run ? `/workspaces/${workspaceId}/workflows/${run.id}` : null;
  const jobActive = !!run?.job && ["queued", "running"].includes(run.job.status);
  const poll = pending || jobActive;

  useEffect(() => {
    let active = true;
    api<DraftConfig>(base + "/response-config").then(value => {
      if (active) setConfig(value);
    }).catch(e => { if (active) setError(workflowError(e)); });
    return () => { active = false; };
  }, [base]);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let polls = 0;
    async function load() {
      if (document.visibilityState === "hidden" && poll) {
        timer = setTimeout(load, 5000); return;
      }
      try {
        const value = await api<ResultPage<Workflow>>(`${base}/workflows?page=${page}&page_size=5`);
        if (active) setHistory(value);
      } catch (e) {
        if (active) setError(workflowError(e));
      } finally {
        if (active) {
          setLoading(false);
          polls += 1;
          if (poll && polls < 60) timer = setTimeout(load, 2000);
          else if (poll) setPollExpired(true);
        }
      }
    }
    void load();
    return () => { active = false; clearTimeout(timer); };
  }, [base, page, refresh, poll, selected]);

  function reload() { setPollExpired(false); setError(""); setLoading(true); setRefresh(value => value + 1); }

  async function perform(action: "start" | "resume" | "cancel") {
    if (busy.current || (action !== "start" && !location)) return;
    busy.current = true; setPending(true); setPollExpired(false); setError("");
    try {
      if (action === "start") {
        requestId.current ??= crypto.randomUUID();
        const result = await api<Workflow>(base + "/workflows", "POST", {
          request_id: requestId.current, expected_ticket_version: ticket.version,
          synthetic_confirmed: confirmed,
        });
        requestId.current = null;
        setHistory(previous => ({ items: [result, ...(previous?.items ?? []).filter(item => item.id !== result.id)].slice(0, 5),
          total: (previous?.total ?? 0) + 1, pages: Math.max(1, previous?.pages ?? 1), page: 1, page_size: 5 }));
        setSelected(result.id); setPage(1);
      } else {
        await api<Workflow>(`${location}/${action}`, "POST", {});
      }
    } catch (e) {
      // Keep the request UUID after an uncertain transport result; never silently generate again.
      setError(workflowError(e));
    } finally {
      busy.current = false; setPending(false); setRefresh(value => value + 1);
    }
  }

  async function review(action: "approved" | "rejected" | "needs_revision") {
    if (!run?.draft || !location || busy.current) return;
    busy.current = true; setPending(true); setPollExpired(false); setError("");
    try {
      await api<Draft>(`${base}/drafts/${run.draft.id}/review`, "POST", {
        expected_version: run.draft.version, action,
      });
      await api<Workflow>(location + "/resume", "POST", {});
    } catch (e) {
      setError(workflowError(e));
    } finally {
      busy.current = false; setPending(false); setRefresh(value => value + 1);
    }
  }

  return <section className="workspace-card workflow-panel" aria-label="AI workflow" aria-busy={loading || pending}>
    <div className="card-heading">
      <div><span className="eyebrow">GUIDED TICKET PROCESSING</span><h2>AI workflow</h2></div>
      <button className="subtle-button" disabled={loading} onClick={reload}>Refresh workflow</button>
    </div>
    <p className="field-help">Classify, gather evidence and prepare a draft for your review. Recommendations do not change this ticket. Approval records an internal decision; nothing is sent.</p>
    {config?.fixture && <p className="role-badge">Deterministic test fixture · not Gemini inference</p>}
    {config && !config.available && <p className="field-help">Live generation is disabled for this workspace. Local recommendations and evidence checks remain available.</p>}
    {editable && config?.available && config.synthetic_confirmation_required && <label className="draft-confirmation">
      <input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} disabled={pending} />
      I confirm this ticket and its knowledge base contain only synthetic data for the approved free-tier API.
    </label>}
    <div className="ticket-actions">
      {editable && <button className="action-button" onClick={() => void perform("start")}
        disabled={pending || loading || !config || (!!config.available && config.synthetic_confirmation_required && !confirmed)}>
        {pending ? "Processing workflow…" : "Start AI workflow"}
      </button>}
      {editable && run?.can_resume && <button className="subtle-button"
        disabled={pending || (run.status === "paused" && run.approval_status === "pending_review")}
        onClick={() => void perform("resume")}>{run.status === "paused" ? "Resume reviewed workflow" : "Recover interrupted workflow"}</button>}
      {editable && run && ["running", "paused"].includes(run.status) && <button className="subtle-button"
        disabled={pending || run.cancel_requested} onClick={() => void perform("cancel")}>Stop workflow</button>}
    </div>
    {pending && <p role="status">Processing request. Stages below reflect saved server progress.</p>}
    {error && <p role="alert" className="form-error">{error}</p>}
    {loading && <p role="status">Loading workflows…</p>}
    {!loading && history?.total === 0 && <div className="workflow-empty">
      <h3>No workflows yet</h3><p>Start with an indexed knowledge base. Each execution pauses for a person to review its draft and sources.</p>
    </div>}
    {!!history?.items.length && <label className="draft-history-label">Workflow history
      <select value={run?.id ?? ""} disabled={pending} onChange={event => setSelected(event.target.value)}>
        {history.items.map(item => <option key={item.id} value={item.id}>
          {dateLabel(item.created_at)} · {workflowLabel(item)} · {item.id.slice(0, 8)}
        </option>)}
      </select>
    </label>}
    {history && history.pages > 1 && <div className="ticket-actions">
      <button className="subtle-button" disabled={pending || page === 1} onClick={() => setPage(value => value - 1)}>Newer workflows</button>
      <span>Page {page} of {history.pages}</span>
      <button className="subtle-button" disabled={pending || page === history.pages} onClick={() => setPage(value => value + 1)}>Older workflows</button>
    </div>}
    {run && <div className="workflow-execution">
      <div className="workflow-status-line"><h3>{workflowLabel(run)}</h3>
        <span className="field-help">Updated {dateLabel(run.updated_at)}</span></div>
      {run.status === "paused" && <p className="field-help">Progress is saved. You can return later to review the exact draft and continue.</p>}
      {run.job?.status === "queued" && <p className="field-help">Your request is saved and queued for a worker. You can leave this page safely.</p>}
      {run.job?.status === "running" && <p className="field-help">A background worker is processing saved workflow stages.</p>}
      {run.cancel_requested && run.status !== "cancelled" && <p role="status">Stop requested. The worker will stop at its next safe execution point.</p>}
      {run.job && <p className="field-help">Worker attempt {run.job.attempts}{run.job.started_at ? ` · Started ${dateLabel(run.job.started_at)}` : ""}{run.job.started_at && run.job.finished_at ? ` · Duration ${Math.round((Date.parse(run.job.finished_at) - Date.parse(run.job.started_at)) / 1000)}s` : ""}</p>}
      {run.job?.error_code && run.job.error_code !== run.error_code && <p role="status">{workflowFailure(run.job.error_code)}</p>}
      {pollExpired && <p role="status">Automatic updates paused after two minutes. Use Refresh workflow to check saved progress.</p>}
      {run.error_code && <p role="alert" className="form-error">{workflowFailure(run.error_code)}</p>}
      <WorkflowStages timings={run.timings_ms} completed={run.completed_stages} current={run.current_stage} failed={run.failed_stage}
        currentLabel={run.status === "paused" ? "Awaiting review" : run.job?.status === "running" ? "In progress" : "Not completed"} />
      <dl className="workflow-summary">
        <div><dt>Category recommendation</dt><dd>{run.classification?.suggested_category ?? (run.classification_unavailable ? "Classifier unavailable · review manually" : run.classification?.uncertain ? "Uncertain · review manually" : "Pending")}</dd></div>
        <div><dt>Priority recommendation</dt><dd>{run.priority ? `${run.priority.suggested_priority} · review required` : "Pending"}</dd></div>
        <div><dt>Selected context</dt><dd>{run.context_summary.passages ?? 0} passages · {run.context_summary.characters ?? 0} characters</dd></div>
        <div><dt>Verification</dt><dd>{run.verification.passed ? run.verification.abstained ? "Abstained · evidence insufficient" : "Citation and basic claim checks passed; human verification required" : "Not completed"}</dd></div>
      </dl>
      {run.priority && <p className="field-help">Priority rules: {run.priority.rule_ids.map(id => id.replaceAll("_", " ")).join(", ")}. Rule matches are suggestions, not a confidence score.</p>}
      {!!run.evidence.length && <div className="workflow-evidence"><h4>Retrieved evidence</h4><ul>
        {run.evidence.map(item => <li key={item.chunk_id}><Link href={`/app/knowledge-base/${item.document_id}?workspace=${workspaceId}`}>
          {item.document_name} · Chunk {item.chunk_index + 1}
        </Link></li>)}
      </ul></div>}
      {run.draft && <DraftCard draft={run.draft} workspaceId={workspaceId}
        editable={editable && run.status === "paused"} pending={pending} loading={loading} review={review} />}
      {run.status === "needs_revision" && <p className="field-help">This execution is closed. Update the ticket or evidence, then deliberately start a new workflow for a new draft and review.</p>}
      <p className="field-help">Started {dateLabel(run.created_at)}{run.finished_at ? ` · Finished ${dateLabel(run.finished_at)}` : ""}</p>
    </div>}
  </section>;
}
