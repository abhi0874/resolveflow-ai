"use client";
import Link from "next/link";
import { useState } from "react";
import { Icon } from "@/components/ui/icon";
import { demoAnalytics } from "@/lib/demo/analytics";
import { label } from "@/lib/analytics";
import type { DemoData } from "@/lib/demo/types";
import { ActivityChart } from "./activity-chart";
export function DemoOverview({ data }: { data: DemoData }) {
  const [window, setWindow]=useState("month");
  const metrics=demoAnalytics(data,window==="month"?"2026-10-01":"2026-10-15","2026-10-21");
  const pending=data.scenarios.filter(s=>!s.decision),reviewed=data.scenarios.filter(s=>s.decision);
  return <div className="dashboard-zones"><div className="dashboard-center">
    <header className="dashboard-welcome"><div><span className="eyebrow">SUPPORT, WITH PERSPECTIVE</span><h1>Your workspace.<br/><span>Understood.</span></h1><p>A clear view of the queue. A considered next move.</p></div><label className="period-control"><span>Example period</span><select aria-label="Overview period" value={window} onChange={e=>setWindow(e.target.value)}><option value="month">October 2026</option><option value="week">Oct 15–21, 2026</option></select></label></header>
    <div className="overview-statline">{[["Support tickets",data.tickets.length,"inbox"],["Knowledge documents",data.documents.length,"book"],["Workflow examples",data.scenarios.length,"workflow"],["Awaiting review",pending.length,"review"]].map(([title,value,icon],i)=><article aria-label={String(title)} key={title} className={i===0?"featured-stat":""}><Icon name={icon as "inbox"} width="18"/><h3>{title}</h3><strong>{value}</strong><span>Workspace total</span></article>)}</div>
    <ActivityChart requests={metrics.tickets.created_trend} resolutions={metrics.tickets.resolution_trend}/>
    <section className="intelligence-strip"><div className="intelligence-orb" aria-hidden="true"><Icon name="spark" width="30" height="30"/></div><div><span className="eyebrow">FROM SIGNAL TO A CONSIDERED RESPONSE</span><h2>AI assists. You decide.</h2><p>Explore classification, evidence and an exact-draft review.</p></div><Link className="action-button" href="/demo/workflows/billing">Explore a workflow ↗</Link></section>
    <section className="dashboard-inbox"><header><h2>In focus</h2><Link href="/demo/tickets">Open inbox ↗</Link></header><div className="compact-ticket-table" role="region" aria-label="Recent synthetic tickets" tabIndex={0}><table><thead><tr><th scope="col">Conversation</th><th scope="col">Category</th><th scope="col">Status</th><th scope="col">Priority</th></tr></thead><tbody>{data.tickets.slice(0,5).map(t=><tr key={t.id}><td><Link href={`/demo/tickets/${t.id}`}>{t.title}</Link><small>{t.customer.split(" ·")[0]}</small></td><td>{t.category}</td><td><span className={`ticket-badge ticket-badge-${t.status}`}>{label(t.status)}</span></td><td><span className="demo-priority" data-priority={t.priority}>{label(t.priority)}</span></td></tr>)}</tbody></table></div></section>
    <div className="dashboard-footnote"><span className="small-dot"/> A self-contained demonstration. Counts reflect synthetic records and your tab-local edits.</div>
  </div><aside className="dashboard-context" aria-label="Workspace context">
    <section className="context-review"><header><span className="eyebrow">YOUR NEXT DECISION</span><Icon name="review"/></header><strong className="context-number">{pending.length.toString().padStart(2,"0")}</strong><h2>Drafts waiting for<br/>a human perspective.</h2><div className="context-queue">{pending.map(s=><Link key={s.id} href={`/demo/workflows/${s.id}`}><span><small>{s.category}</small>{s.title}</span><span aria-hidden="true">↗</span></Link>)}{!pending.length&&<p>All example drafts reviewed. Reset the demo to start again.</p>}</div></section>
    <section className="context-activity"><header><h2>Recent decisions</h2><span className="context-pill">{reviewed.length}</span></header><ol>{reviewed.map(s=><li key={s.id}><span className="activity-dot"/><div><Link href={`/demo/workflows/${s.id}`}>{s.title}</Link><small>{label(s.decision!)} · synthetic record</small></div></li>)}</ol>{!reviewed.length&&<p>Your review decisions will appear here.</p>}</section>
    <section className="context-engineering"><span className="eyebrow">BEYOND THE INTERFACE</span><h2>Real engineering.<br/>Honest boundaries.</h2><p>Python, scikit-learn, pgvector and LangGraph—implemented and evaluated locally.</p><Link href="/demo/architecture">Under the hood <span aria-hidden="true">↗</span></Link></section>
    <div className="context-shortcuts"><span className="eyebrow">TAKE A CLOSER LOOK</span><Link href="/demo/knowledge"><Icon name="book" width="18"/> Browse source evidence ↗</Link><Link href="/demo/analytics"><Icon name="chart" width="18"/> Explore analytics ↗</Link></div>
  </aside></div>;
}
