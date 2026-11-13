"use client";
import { DemoOverview } from "./overview";
import { WorkspaceNavigation, demoNavigation as navigation } from "./navigation";
import Link from "next/link";
import { useState, useSyncExternalStore } from "react";
import { createDemoSource } from "@/lib/demo/store";
import type { Action } from "@/lib/demo/types";

import { DemoAnalytics } from "./analytics";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { DemoTickets } from "./tickets";
import { DemoKnowledge } from "./knowledge";
import { DemoWorkflows } from "./workflows";
import { DemoArchitecture } from "./architecture";
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
  function dispatch(action: Action) {
    try { if (source) { setData(source.dispatch(action)); setMessage(source.notice || "Updated in this browser tab only. Nothing was sent to a server."); } }
    catch (error) { setMessage(error instanceof Error ? error.message : "This change could not be saved."); }
  }
  return <main className={`workspace-page demo-page structural-demo page-${section}`} id="main-content">
    <a href="#demo-content" className="skip-link">Skip to demo content</a>
    <WorkspaceNavigation section={section} data={data} onReset={() => setResetting(true)} />
    <section className="workspace-content ticket-content" id="demo-content" tabIndex={-1}>
      <header className="demo-toolbar"><div className="workspace-breadcrumb"><span className="workspace-dot" /> <span>Northstar Studio</span><span aria-hidden="true">/</span><strong>{navigation.find(([key]) => key === section)?.[1] ?? "Overview"}</strong></div><span className="workspace-edition"><span className="small-dot" /> INTERACTIVE PORTFOLIO</span></header>
      <div className="demo-notice"><span className="role-badge">SYNTHETIC WORKSPACE</span><p>Precomputed examples. No live AI. Changes stay in this tab.</p><Link href="/demo/architecture">How it works ↗</Link></div>
      {resetting && <ConfirmDialog title="Start fresh?" description="This removes only this tab’s demo edits and decisions." confirmLabel="Confirm reset" onCancel={() => setResetting(false)} onConfirm={() => { if (source) setData(source.reset()); setResetting(false); setMessage("Demo reset. Original synthetic examples restored."); }} />}
      {message && <p role="status" className="demo-feedback">{message}</p>}
      {!source ? <div className="analytics-loading" role="status"><p>Preparing your synthetic workspace…</p><div className="analytics-skeleton" /></div> : <>
        {section === "overview" && <DemoOverview data={data} />}
        {section === "tickets" && <DemoTickets data={data} selected={selected} dispatch={dispatch} />}
        {section === "knowledge" && <DemoKnowledge data={data} selected={selected} />}
        {section === "workflows" && <DemoWorkflows key={selected ?? "index"} data={data} selected={selected} dispatch={dispatch} />}
        {section === "analytics" && <DemoAnalytics data={data} />}
        {section === "architecture" && <DemoArchitecture />}
      </>}
    </section>
  </main>;
}
