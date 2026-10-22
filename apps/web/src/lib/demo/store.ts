import { agents, fixtures } from "./fixtures";
import { priorities, statuses, type Action, type DemoData, type DemoDataSource } from "./types";
export const STORAGE_KEY = "resolveflow-demo-v1";
const stamp = "2026-10-21T12:00:00Z";
const text = (v: unknown, max: number) => typeof v === "string" && v.trim().length > 0 && v.length <= max;
export function validAction(value: unknown): value is Action {
  if (!value || typeof value !== "object") return false;
  const a = value as Record<string, unknown>;
  switch (a.type) {
    case "create": return text(a.title, 120) && text(a.body, 1200) && priorities.includes(a.priority as never) && Object.keys(a).length === 4;
    case "status": return text(a.id, 60) && statuses.includes(a.value as never) && Object.keys(a).length === 3;
    case "assign": return text(a.id, 60) && agents.includes(a.value as string) && Object.keys(a).length === 3;
    case "note": return text(a.id, 60) && text(a.value, 500) && Object.keys(a).length === 3;
    case "review": return text(a.id, 60) && ["approved", "rejected", "needs_revision"].includes(a.value as string) && Object.keys(a).length === 3;
    default: return false;
  }
}
export function apply(data: DemoData, action: Action): DemoData {
  if (!validAction(action)) throw new Error("Invalid demo action.");
  const next = structuredClone(data);
  if (action.type === "create") {
    if (next.tickets.length >= 28) throw new Error("This demo supports 20 temporary tickets. Reset to start again.");
    next.tickets.unshift({ id: `local-${next.tickets.length}`, title: action.title.trim(), body: action.body.trim(), category: "Uncategorized", priority: action.priority, status: "open", assignee: "Unassigned", customer: "Visitor · synthetic customer", created: stamp, resolved: null, notes: [], activity: ["Temporary ticket created in this browser tab"] });
  } else if (action.type === "review") {
    const scenario = next.scenarios.find(s => s.id === action.id);
    if (!scenario || scenario.decision) throw new Error("This example already has a decision. Reset to review again.");
    if (scenario.abstained && action.value === "approved") throw new Error("An abstention requires escalation or revision, not approval.");
    scenario.decision = action.value; scenario.finished = stamp;
  } else {
    const ticket = next.tickets.find(t => t.id === action.id);
    if (!ticket) throw new Error("Demo ticket not found.");
    if (action.type === "status") {
      if (ticket.status === action.value) return data;
      ticket.resolved = action.value === "resolved" ? stamp : action.value === "closed" ? ticket.resolved : null;
      ticket.status = action.value; ticket.activity.push(`Local status changed to ${action.value.replaceAll("_", " ")}`);
    } else if (action.type === "assign") { ticket.assignee = action.value; ticket.activity.push(`Local assignment changed to ${action.value}`); }
    else { ticket.notes.push(action.value.trim()); ticket.activity.push("Local internal note added"); }
  }
  return next;
}
export function createDemoSource(storage?: Pick<Storage, "getItem" | "setItem" | "removeItem">): DemoDataSource & { notice: string } {
  let actions: Action[] = []; let data = fixtures(); let notice = "";
  try {
    const raw = storage?.getItem(STORAGE_KEY);
    if (raw) {
      if (raw.length > 180000) throw new Error("Too large");
      const parsed: unknown = JSON.parse(raw);
      if (!Array.isArray(parsed) || parsed.length > 100 || !parsed.every(validAction)) throw new Error("Invalid saved state");
      for (const action of parsed) data = apply(data, action);
      actions = parsed;
    }
  } catch { data = fixtures(); actions = []; notice = "Saved demo data could not be restored. A fresh example is ready."; }
  return { notice, read: () => structuredClone(data), dispatch(action) {
    if (actions.length >= 100) throw new Error("Demo interaction limit reached. Reset to start again.");
    data = apply(data, action); actions.push(action);
    try { storage?.setItem(STORAGE_KEY, JSON.stringify(actions)); } catch { this.notice = "Browser storage is unavailable. Changes last until you leave this page."; }
    return this.read();
  }, reset() { data = fixtures(); actions = []; try { storage?.removeItem(STORAGE_KEY); } catch { this.notice = "Browser storage is unavailable; this reset applies to the open page."; } return this.read(); } };
}
