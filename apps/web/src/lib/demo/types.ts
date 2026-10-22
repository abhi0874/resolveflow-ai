export const statuses = ["open", "in_progress", "waiting_for_approval", "resolved", "closed"] as const;
export const priorities = ["low", "medium", "high", "urgent"] as const;
export type Status = typeof statuses[number];
export type Priority = typeof priorities[number];
export type Decision = "approved" | "rejected" | "needs_revision";
export type DemoTicket = { id: string; title: string; body: string; customer: string; category: string; priority: Priority; status: Status; assignee: string; created: string; resolved: string | null; notes: string[]; activity: string[] };
export type DemoDocument = { id: string; title: string; summary: string; created: string; passages: { id: string; heading: string; text: string }[] };
export type Scenario = { id: string; ticketId: string; title: string; category: string; priority: Priority; evidence: string[]; draft: string; abstained: boolean; reason: string; decision: Decision | null; created: string; finished: string | null };
export type DemoData = { tickets: DemoTicket[]; documents: DemoDocument[]; scenarios: Scenario[] };
export type Action =
  | { type: "status"; id: string; value: Status }
  | { type: "assign"; id: string; value: string }
  | { type: "note"; id: string; value: string }
  | { type: "create"; title: string; body: string; priority: Priority }
  | { type: "review"; id: string; value: Decision };
export interface DemoDataSource { read(): DemoData; dispatch(action: Action): DemoData; reset(): DemoData }
