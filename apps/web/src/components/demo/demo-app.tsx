"use client";
import { DemoOverview } from "./overview";
import { Icon, type IconName } from "@/components/ui/icon";
import { Brand } from "@/components/layout/brand";
import { ThemeSwitcher } from "@/components/ui/theme-switcher";
import Link from "next/link";
import { useMemo, useState, useSyncExternalStore } from "react";
import { createDemoSource } from "@/lib/demo/store";
import type { Action } from "@/lib/demo/types";
import { demoAnalytics } from "@/lib/demo/analytics";
import { AnalyticsDashboard } from "@/components/analytics/dashboard";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DemoTickets } from "./tickets";
import { DemoKnowledge } from "./knowledge";
import { DemoWorkflows } from "./workflows";
import { DemoArchitecture } from "./architecture";
const navigation = [["overview", "Overview", "overview"], ["tickets", "Ticket inbox", "inbox"], ["knowledge", "Knowledge base", "book"], ["workflows", "AI workflows", "workflow"], ["analytics", "Analytics", "chart"], ["architecture", "Under the hood", "classify"]];
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
      <Brand />
      <div className="workspace-navigation"><span className="eyebrow">EXAMPLE WORKSPACE</span><div className="demo-workspace"><span className="workspace-avatar">N</span><div>Northstar Studio<small>Support operations · synthetic</small></div></div>
        <nav className="ticket-nav" aria-label="Demo navigation">{navigation.map(([key, title, icon]) => <Link key={key} href={key === "overview" ? "/demo" : `/demo/${key}`} aria-current={section === key ? "page" : undefined}><Icon name={icon as IconName} width="20" height="20" /> <span>{title}</span></Link>)}</nav>
      </div>
      <div className="workspace-account"><span className="eyebrow">YOUR PRIVATE SANDBOX</span><p>No account. No external actions.<br />Changes stay in this browser tab.</p><button className="subtle-button" onClick={() => setResetting(true)} disabled={!source}>Reset demo</button></div>
    </aside>
    <section className="workspace-content ticket-content" id="demo-content" tabIndex={-1}>
      <header className="demo-toolbar"><div className="workspace-breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><strong>{navigation.find(([key]) => key === section)?.[1] ?? "Overview"}</strong></div><ThemeSwitcher /></header>
      <div className="demo-notice"><span className="role-badge">SYNTHETIC DEMO</span><p>Explore freely. Workflow examples are precomputed, not live AI. Please enter synthetic information only.</p><Link href="/demo/architecture">How it works ↗</Link></div>
      {resetting && <ConfirmDialog title="Start fresh?" description="This removes only this tab’s demo edits and decisions." confirmLabel="Confirm reset" onCancel={() => setResetting(false)} onConfirm={() => { if (source) setData(source.reset()); setResetting(false); setMessage("Demo reset. Original synthetic examples restored."); }} />}
      {message && <p role="status" className="demo-feedback">{message}</p>}
      {!source ? <div className="analytics-loading" role="status"><p>Preparing your synthetic workspace…</p><div className="analytics-skeleton" /></div> : <>
        {section === "overview" && <DemoOverview data={data} />}
        {section === "tickets" && <DemoTickets data={data} selected={selected} dispatch={dispatch} />}
        {section === "knowledge" && <DemoKnowledge data={data} selected={selected} />}
        {section === "workflows" && <DemoWorkflows key={selected ?? "index"} data={data} selected={selected} dispatch={dispatch} />}
        {section === "analytics" && <AnalyticsDashboard workspaceId="synthetic-demo" source={analyticsSource} />}
        {section === "architecture" && <DemoArchitecture />}
      </>}
    </section>
  </main>;
}
