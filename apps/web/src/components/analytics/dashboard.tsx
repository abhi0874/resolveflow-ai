"use client";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/session-api";
import { count, duration, rate, type Analytics, type Measurement } from "@/lib/analytics";
import { Distribution, TrendChart } from "./charts";

function Metric({ title, value, note }: { title: string; value: string; note: string }) {
  return <article className="analytics-metric" aria-label={title}><h3>{title}</h3><strong>{value}</strong><p>{note}</p></article>;
}
function Measured({ title, data, format = duration, note }: { title: string; data: Measurement; format?: (v: number) => string; note: string }) {
  return <Metric title={title} value={data.value === null ? "Unavailable" : format(data.value)}
    note={data.value === null ? `${note}. ${data.unavailable_reason ?? "Not measurable from retained records."}` : `${note} · ${count(data.samples)} eligible records`} />;
}
function defaults() {
  const end = new Date(); const start = new Date(end); start.setUTCDate(end.getUTCDate() - 29);
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}
export type AnalyticsSource = { load: (start: string, end: string) => Promise<Analytics>; description: string; dates: { start: string; end: string } };
export function AnalyticsDashboard({ workspaceId, source }: { workspaceId: string; source?: AnalyticsSource }) {
  const [dates, setDates] = useState(() => source?.dates ?? defaults());
  const [selection, setSelection] = useState(() => ({ ...(source?.dates ?? defaults()), revision: 0 }));
  const [result, setResult] = useState<{ key: string; data?: Analytics; error?: string } | null>(null);
  const key = `${workspaceId}:${selection.start}:${selection.end}:${selection.revision}`;
  const current = result?.key === key ? result : null;
  useEffect(() => {
    let active = true;
    (source ? source.load(selection.start, selection.end) : api<Analytics>(`/workspaces/${workspaceId}/analytics/overview?start=${selection.start}&end=${selection.end}`))
      .then(data => { if (active) setResult({ key, data }); })
      .catch(error => { if (active) setResult({ key, error: errorMessage(error) }); });
    return () => { active = false; };
  }, [workspaceId, selection.start, selection.end, key, source]);
  const data = current?.data;
  const invalid = !dates.start || !dates.end || dates.start > dates.end || dates.end > defaults().end ||
    (Date.parse(dates.end) - Date.parse(dates.start)) / 86400000 >= 366;
  return <div className="analytics-dashboard">
    <header className="analytics-heading"><span className="eyebrow">WORKSPACE INTELLIGENCE</span><h1>Analytics</h1>
      <p>{source?.description ?? "Support activity, human decisions and workflow reliability. Measured from your workspace records."}</p></header>
    <form className="workspace-card analytics-filter" onSubmit={event => { event.preventDefault(); if (!invalid) setSelection({ ...dates, revision: selection.revision + 1 }); }}>
      <label>From (UTC)<input type="date" value={dates.start} max={dates.end} required onChange={event => setDates({ ...dates, start: event.target.value })} /></label>
      <label>Through (UTC)<input type="date" value={dates.end} min={dates.start} max={defaults().end} required onChange={event => setDates({ ...dates, end: event.target.value })} /></label>
      <button className="action-button" disabled={invalid || !current}>Apply range</button>
      <p className="field-help">Inclusive UTC days · up to 366 days. Distributions show current outcomes of records created in the selected range.</p>
      {invalid && <p role="alert">Choose an ordered range of at most 366 days, ending today or earlier.</p>}
    </form>
    {!current && <div className="analytics-loading" role="status" aria-label="Loading analytics"><p>Loading workspace analytics…</p><div className="analytics-metrics">{[0, 1, 2, 3].map(i => <div key={i} className="analytics-skeleton" />)}</div></div>}
    {current?.error && <section className="workspace-card"><p role="alert">{current.error}</p><button className="subtle-button" onClick={() => setSelection({ ...selection, revision: selection.revision + 1 })}>Retry analytics</button></section>}
    {data && <>
      <p className="field-help">Showing {data.range.start} through {data.range.end} UTC · Retrieved {new Date(data.generated_at).toLocaleTimeString()}.</p>
      {data.tickets.total + data.workflows.total + data.knowledge_base.total === 0 && <section className="analytics-empty workspace-card"><h2>No activity in this range</h2><p>Choose another range or create tickets and upload knowledge documents to begin measuring activity.</p></section>}
      <div className="analytics-metrics">
        <Metric title="Tickets created" value={count(data.tickets.total)} note="Creation-date cohort; current status below" />
        <Measured title="Median resolution time" data={data.tickets.resolution_median_seconds} note="Creation to latest recorded resolution, including reopen time" />
        <Metric title="Workflow executions" value={count(data.workflows.total)} note="Unique requested workflows; retries are not extra executions" />
        <Measured title="Internal approval rate" data={data.reviews.approval_rate} format={rate} note="Approved / all reviewed drafts; nothing sent" />
      </div>
      <div className="analytics-grid"><TrendChart title="Ticket creation trend" points={data.tickets.created_trend} /><TrendChart title="Recorded resolution trend" points={data.tickets.resolution_trend} /></div>
      <div className="analytics-grid analytics-three"><Distribution title="Ticket status" buckets={data.tickets.statuses} /><Distribution title="Ticket priority" buckets={data.tickets.priorities} /><Distribution title="Ticket categories" buckets={data.tickets.categories} /></div>
      <section className="workspace-card"><h2>How resolution is measured</h2><p>For currently resolved or closed tickets in this creation cohort, time runs from creation to the latest recorded resolution, including reopened periods. Complete, consistent status history is required. The trend shows their latest resolutions within the selected range.</p><p>{count(data.tickets.resolution_history_excluded)} resolved/closed tickets excluded because history is insufficient or inconsistent. Never-resolved and currently reopened tickets are not duration samples.</p>
        <Measured title="Average resolution time" data={data.tickets.resolution_average_seconds} note="Valid history only" /></section>
      <div className="analytics-section-title"><span className="eyebrow">AI & HUMAN OVERSIGHT</span><h2>Workflow outcomes</h2><p>Paused work is waiting for a person. Approval records an internal decision, never customer delivery.</p></div>
      <div className="analytics-metrics"><Measured title="Workflow completion rate" data={data.workflows.success_rate} format={rate} note="Completed / all terminal outcomes" /><Measured title="Workflow failure rate" data={data.workflows.failure_rate} format={rate} note="Failed / all terminal outcomes" /><Measured title="Workflow elapsed time" data={data.workflows.elapsed_average_seconds} note="Creation to terminal finish; includes queue and human wait" /><Measured title="Time to review" data={data.reviews.request_to_review_average_seconds} note="Draft request to saved decision; includes generation" /></div>
      <div className="analytics-grid analytics-three"><Distribution title="Workflow status" buckets={data.workflows.statuses} /><Distribution title="Last saved stage" buckets={data.workflows.stages} /><Distribution title="Human review outcomes" buckets={data.reviews.outcomes} note="Successfully generated drafts in the creation cohort" /></div>
      <div className="analytics-section-title"><span className="eyebrow">BACKGROUND PROCESSING</span><h2>Job performance</h2><p>Queue status is current across this workspace, independent of the date filter. Historical measurements use jobs created in the selected range.</p></div>
      <div className="analytics-metrics"><Metric title="Jobs created" value={count(data.jobs.cohort_total)} note="One job per workflow" /><Metric title="Retained phase retries" value={count(data.jobs.retained_phase_retries)} note="Sum of max(attempts − 1, 0); resets on resume; not lifetime retries" /><Measured title="Initial queue wait" data={data.jobs.initial_wait_average_seconds} note="First start attempts only; resume/retry wait unavailable" /><Measured title="Latest attempt duration" data={data.jobs.latest_attempt_average_seconds} note="Retained start/finish timestamps, not total processing time" /></div>
      <Distribution title="Current job status" buckets={data.jobs.current_statuses} />
      <div className="analytics-section-title"><span className="eyebrow">KNOWLEDGE COVERAGE</span><h2>Knowledge base</h2><p>Current surviving documents uploaded in the range. Extraction and vector indexing are separate steps; deleted uploads are not retained.</p></div>
      <div className="analytics-metrics"><Metric title="Documents uploaded" value={count(data.knowledge_base.total)} note="Excludes deleting documents" /><Metric title="Successfully processed" value={count(data.knowledge_base.processed)} note="Text extraction completed" /><Metric title="Indexed documents" value={count(data.knowledge_base.indexed)} note="Current indexing status is indexed" /><Metric title="Stored chunks" value={count(data.knowledge_base.chunks)} note={`${count(data.knowledge_base.failed)} documents failed processing`} /></div>
      <TrendChart title="Document upload trend" points={data.knowledge_base.upload_trend} />
    </>}
  </div>;
}
