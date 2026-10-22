export type Bucket = { label: string; count: number };
export type Point = { day: string; count: number };
export type Measurement = { value: number | null; samples: number; unavailable_reason: string | null };
export type Analytics = {
  range: { start: string; end: string }; generated_at: string;
  tickets: { total: number; statuses: Bucket[]; priorities: Bucket[]; categories: Bucket[];
    created_trend: Point[]; resolution_trend: Point[]; resolution_average_seconds: Measurement;
    resolution_median_seconds: Measurement; resolution_history_excluded: number };
  workflows: { total: number; statuses: Bucket[]; stages: Bucket[]; success_rate: Measurement;
    failure_rate: Measurement; elapsed_average_seconds: Measurement };
  jobs: { current_statuses: Bucket[]; cohort_total: number; retained_phase_retries: number;
    latest_attempt_average_seconds: Measurement; initial_wait_average_seconds: Measurement };
  reviews: { total_completed_drafts: number; outcomes: Bucket[]; approval_rate: Measurement;
    request_to_review_average_seconds: Measurement };
  knowledge_base: { total: number; processed: number; failed: number; indexed: number; chunks: number; upload_trend: Point[] };
};
export const count = (value: number) => new Intl.NumberFormat("en-US").format(value);
export const label = (value: string) => value.replaceAll("_", " ");
export const rate = (value: number) => new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 }).format(value);
export function duration(value: number) {
  if (value < 60) return `${Math.round(value)} sec`;
  if (value < 3600) return `${(value / 60).toFixed(1)} min`;
  return `${(value / 3600).toFixed(1)} hr`;
}
