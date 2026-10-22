import type { Analytics, Measurement } from "../analytics";
import type { DemoData } from "./types";
import { priorities, statuses } from "./types";
const missing = (): Measurement => ({ value: null, samples: 0, unavailable_reason: "Not recorded in this demonstration" });
const measured = (values: number[]): Measurement => values.length ? ({ value: values.reduce((a, b) => a + b, 0) / values.length, samples: values.length, unavailable_reason: null }) : missing();
const ratio = (n: number, d: number): Measurement => d ? { value: n / d, samples: d, unavailable_reason: null } : missing();
const groups = (labels: string[], keys?: readonly string[]) => (keys ?? [...new Set(labels)]).map(label => ({ label, count: labels.filter(x => x === label).length }));
export function demoAnalytics(data: DemoData, start: string, end: string): Analytics {
  const from = Date.parse(start), to = Date.parse(end);
  if (!Number.isFinite(from) || !Number.isFinite(to) || from > to || (to - from) / 86400000 >= 366) throw new Error("Choose a valid range up to 366 days.");
  const within = (date: string) => date.slice(0, 10) >= start && date.slice(0, 10) <= end;
  const trend = (dates: string[]) => Array.from({ length: (to - from) / 86400000 + 1 }, (_, i) => {
    const day = new Date(from + i * 86400000).toISOString().slice(0, 10);
    return { day, count: dates.filter(d => d.startsWith(day)).length };
  });
  const tickets = data.tickets.filter(t => within(t.created));
  const resolved = tickets.filter(t => ["resolved", "closed"].includes(t.status) && t.resolved);
  const seconds = resolved.map(t => (Date.parse(t.resolved!) - Date.parse(t.created)) / 1000).sort((a, b) => a - b);
  const median = measured(seconds); if (seconds.length) median.value = (seconds[Math.floor((seconds.length - 1) / 2)] + seconds[Math.floor(seconds.length / 2)]) / 2;
  const runs = data.scenarios.filter(s => within(s.created));
  const reviewed = runs.filter(s => s.decision); const completed = reviewed.filter(s => s.decision === "approved").length;
  const durations = reviewed.filter(s => s.finished).map(s => (Date.parse(s.finished!) - Date.parse(s.created)) / 1000);
  const docs = data.documents.filter(d => within(d.created));
  return {
    range: { start, end }, generated_at: new Date().toISOString(),
    tickets: { total: tickets.length, statuses: groups(tickets.map(t => t.status), statuses), priorities: groups(tickets.map(t => t.priority), priorities), categories: groups(tickets.map(t => t.category)), created_trend: trend(tickets.map(t => t.created)), resolution_trend: trend(resolved.map(t => t.resolved!)), resolution_average_seconds: measured(seconds), resolution_median_seconds: median, resolution_history_excluded: tickets.filter(t => ["resolved", "closed"].includes(t.status) && !t.resolved).length },
    workflows: { total: runs.length, statuses: groups(runs.map(s => s.decision === "approved" ? "completed" : s.decision ?? "paused")), stages: groups(runs.map(() => "approval")), success_rate: ratio(completed, reviewed.length), failure_rate: ratio(0, reviewed.length), elapsed_average_seconds: measured(durations) },
    jobs: { current_statuses: [], cohort_total: 0, retained_phase_retries: 0, latest_attempt_average_seconds: missing(), initial_wait_average_seconds: missing() },
    reviews: { total_completed_drafts: runs.length, outcomes: groups(runs.map(s => s.decision ?? "pending_review"), ["pending_review", "approved", "rejected", "needs_revision"]), approval_rate: ratio(completed, reviewed.length), request_to_review_average_seconds: measured(durations) },
    knowledge_base: { total: docs.length, processed: docs.length, failed: 0, indexed: 0, chunks: docs.reduce((sum, d) => sum + d.passages.length, 0), upload_trend: trend(docs.map(d => d.created)) },
  };
}
