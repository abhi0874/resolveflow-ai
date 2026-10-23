"use client";
import Link from "next/link";
import { useMemo, useState, useSyncExternalStore } from "react";
import { createDemoSource } from "@/lib/demo/store";
import type { Action } from "@/lib/demo/types";
import { demoAnalytics } from "@/lib/demo/analytics";
import { AnalyticsDashboard } from "@/components/analytics/dashboard";
import { DemoTickets } from "./tickets";
import { DemoKnowledge } from "./knowledge";
import { DemoWorkflows } from "./workflows";
import { DemoArchitecture } from "./architecture";
const navigation = [["overview", "Overview", "◈"], ["tickets", "Ticket inbox", "◫"], ["knowledge", "Knowledge base", "▤"], ["workflows", "AI workflows", "⌘"], ["analytics", "Analytics", "◴"], ["architecture", "Under the hood", "◇"]];
const subscribe = () => () => {};
const hydrated = () => true;
const notHydrated = () => false;
export function DemoApp(props: { section: string; selected?: string }) {
  const ready = useSyncExternalStore(subscribe, hydrated, notHydrated);
  return ready ? <DemoWorkspace {...props} /> : <main className="workspace-content" role="status">Preparing your synthetic workspace…</main>;
}
function DemoWorkspace({ section, selected }: { section: string; selected?: string }) {
  const [source] = useState(() => {
    try { return createDemoSource(window.sessionStorage); } catch { const store = createDemoSource(); store.notice = "Storage is blocked. Changes last only on this page."; return store; }
  });
  const [data, setData] = useState(() => source.read());
  const [message, setMessage] = useState(source.notice);
  const [resetting, setResetting] = useState(false);
  const analyticsSource = useMemo(() => ({ load: async (start: string, end: string) => demoAnalytics(data, start, end), dates: { start: "2026-10-01", end: "2026-10-21" }, description: "Demo Data · Calculated from synthetic October 2026 records and your local changes. Example timestamps are not live operational measurements. No workers or vector indexing run in this demo." }), [data]);
  function dispatch(action: Action) {
    try { if (source) { setData(source.dispatch(action)); setMessage(source.notice || "Updated in this browser tab only. Nothing was sent to a server."); } }
    catch (error) { setMessage(error instanceof Error ? error.message : "This change could not be saved."); }
  }
  return <main className="workspace-page demo-page" id="main-content">
    <a href="#demo-content" className="skip-link">Skip to demo content</a>
    <aside className="workspace-sidebar">
      <Link href="/" className="brand">ResolveFlow <span className="brand-ai">AI</span></Link>
      <div className="workspace-navigation"><span className="eyebrow">EXAMPLE WORKSPACE</span><div className="demo-workspace"><span className="workspace-avatar">N</span><div>Northstar Studio<small>Support operations · synthetic</small></div></div>
        <nav className="ticket-nav" aria-label="Demo navigation">{navigation.map(([key, title, icon]) => <Link key={key} href={key === "overview" ? "/demo" : `/demo/${key}`} aria-current={section === key ? "page" : undefined}><span aria-hidden="true">{icon}</span> &nbsp; {title}</Link>)}</nav>
      </div>
      <div className="workspace-account"><span className="eyebrow">YOUR PRIVATE SANDBOX</span><p>No account. No external actions.<br />Changes stay in this browser tab.</p><button className="subtle-button" onClick={() => setResetting(true)} disabled={!source}>Reset demo</button></div>
    </aside>
    <section className="workspace-content ticket-content" id="demo-content" tabIndex={-1}>
      <div className="demo-notice"><span className="role-badge">SYNTHETIC DEMO</span><p>Explore freely. Workflow examples are precomputed, not live AI. Please enter synthetic information only.</p><Link href="/demo/architecture">How it works ↗</Link></div>
      {resetting && <section className="workspace-card" aria-label="Reset confirmation"><h2>Start fresh?</h2><p>This removes only this tab’s demo edits and decisions.</p><div className="ticket-actions"><button className="action-button" onClick={() => { if (source) setData(source.reset()); setResetting(false); setMessage("Demo reset. Original synthetic examples restored."); }}>Confirm reset</button><button className="subtle-button" onClick={() => setResetting(false)}>Keep exploring</button></div></section>}
      {message && <p role="status" className="demo-feedback">{message}</p>}
      {!source ? <div className="analytics-loading" role="status"><p>Preparing your synthetic workspace…</p><div className="analytics-skeleton" /></div> : <>
        {section === "overview" && <><header className="demo-heading"><span className="eyebrow">A CALMER WAY TO SUPPORT</span><h1>Every request.<br /><em>A considered response.</em></h1><p>Explore ticket triage, citation-backed drafts and human review in a synthetic support workspace. Start with a workflow, then inspect the architecture behind the full application.</p><div className="ticket-actions"><Link className="action-button" href="/demo/workflows/billing">Explore a workflow ↗</Link><Link className="subtle-button" href="/demo/tickets">Browse the inbox</Link></div></header>
          <div className="analytics-metrics demo-summary">{[["Support tickets", data.tickets.length], ["Knowledge documents", data.documents.length], ["Workflow examples", data.scenarios.length], ["Awaiting review", data.scenarios.filter(s => !s.decision).length]].map(([title, value]) => <article className="analytics-metric" key={title} aria-label={String(title)}><h3>{title}</h3><strong>{value}</strong><p>Synthetic workspace records</p></article>)}</div>
          <div className="demo-section-heading"><div><span className="eyebrow">FOLLOW THE EVIDENCE</span><h2>Five requests. Different decisions.</h2></div><p>From a straightforward refund question to a request that needs a specialist.</p></div><div className="demo-scenario-grid">{data.scenarios.map((s, i) => <Link className="workspace-card demo-scenario" href={`/demo/workflows/${s.id}`} key={s.id}><span className="eyebrow">0{i + 1} / {s.category}</span><h3>{s.title}</h3><p>{s.abstained ? "See why the system should abstain and escalate." : "Inspect the source, read the draft, make the decision."}</p><span className="demo-card-link">Open example ↗</span></Link>)}</div>
          <section className="workspace-card demo-explainer"><h2>A working product. An honest demonstration.</h2><p>The full application uses persistent LangGraph workflows, tenant-scoped retrieval and human approval. This sandbox presents authored examples of those capabilities without requiring any backend, credentials or AI quota.</p><Link href="/demo/architecture">Explore the architecture ↗</Link></section></>}
        {section === "tickets" && <DemoTickets data={data} selected={selected} dispatch={dispatch} />}
        {section === "knowledge" && <DemoKnowledge data={data} selected={selected} />}
        {section === "workflows" && <DemoWorkflows key={selected ?? "index"} data={data} selected={selected} dispatch={dispatch} />}
        {section === "analytics" && <AnalyticsDashboard workspaceId="synthetic-demo" source={analyticsSource} />}
        {section === "architecture" && <DemoArchitecture />}
      </>}
    </section>
  </main>;
}
