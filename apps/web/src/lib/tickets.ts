import { ApiError, errorMessage } from "./session-api";
export const statuses = {
  open: "Open",
  in_progress: "In progress",
  waiting_for_approval: "Waiting for approval",
  resolved: "Resolved",
  closed: "Closed",
} as const;
export const priorities = {
  low: "Low",
  medium: "Medium",
  high: "High",
  urgent: "Urgent",
} as const;
export type Ticket = {
  id: string;
  workspace_id: string;
  title: string;
  description: string;
  category: string | null;
  status: keyof typeof statuses;
  priority: keyof typeof priorities;
  assigned_user_id: string | null;
  created_at: string;
  updated_at: string;
  version: number;
};
export type TicketNote = {
  id: string;
  body: string;
  author_id: string;
  author_email: string;
  created_at: string;
};
export type Activity = {
  id: string;
  actor_email: string;
  action: string;
  created_at: string;
  details: Record<string, string | string[] | null>;
};
export type ResultPage<T> = {
  items: T[];
  page: number;
  page_size: number;
  pages: number;
  total: number;
};
export function ticketError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404)
      return "This ticket or workspace is unavailable. It may no longer be accessible to you.";
    if (error.status === 409)
      return "This ticket changed since you opened it. Refresh the ticket before saving again.";
    if (error.status === 422)
      return "Check the field lengths and selected values. Assignees must be active support staff in this workspace.";
    if (error.status === 413)
      return "This submission is too large. Shorten the description or note and try again.";
  }
  return errorMessage(error);
}
export function dateLabel(value: string) {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
