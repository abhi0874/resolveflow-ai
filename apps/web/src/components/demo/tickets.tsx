"use client";
import Link from "next/link";
import { useState } from "react";
import { Icon } from "@/components/ui/icon";
import type { Action, DemoData, Priority, Status } from "@/lib/demo/types";
import { priorities, statuses } from "@/lib/demo/types";
import { label } from "@/lib/analytics";
import { agents } from "@/lib/demo/fixtures";
import { useModalDialog } from "@/components/ui/use-modal-dialog";

export function DemoTickets({ data, selected, dispatch }: { data: DemoData; selected?: string; dispatch: (a: Action) => void }) {
  const [search, setSearch] = useState(""); const [status, setStatus] = useState(""); const [priority, setPriority] = useState(""); const [creating, setCreating] = useState(false);
  const items = data.tickets.filter(t => (!status || t.status === status) && (!priority || t.priority === priority) && `${t.title} ${t.body} ${t.category}`.toLowerCase().includes(search.toLowerCase()));
  const ticket = selected ? data.tickets.find(t => t.id === selected) : items[0];
  if (selected && !ticket) return <section className="workspace-card"><h1>Demo ticket not found</h1><Link href="/demo/tickets">Back to tickets</Link></section>;
  const scenario = data.scenarios.find(s => s.ticketId === ticket?.id);
  return <div className={`inbox-experience ${selected ? "has-selection" : "list-first"}`}>
    <header className="page-title-row"><div><span className="eyebrow">THE CONVERSATION STARTS HERE</span><h1>Ticket inbox<span className="title-count">{data.tickets.length}</span></h1></div><button className="action-button" onClick={() => setCreating(true)}>Create demo ticket <span aria-hidden="true">＋</span></button></header>
    <div className="inbox-layout">
      <section className="inbox-list" aria-label="Ticket list"><div className="inbox-list-head"><span className="eyebrow">ALL CONVERSATIONS</span><span>{items.length}</span></div>
        <label className="inbox-search"><Icon name="search" width="18" height="18" /><span className="sr-only">Search tickets</span><input type="search" maxLength={120} value={search} onChange={e => setSearch(e.target.value)} placeholder="Search the inbox…" /></label>
        <div className="inbox-filters"><label><span>Status</span><select aria-label="Filter status" value={status} onChange={e => setStatus(e.target.value)}><option value="">All statuses</option>{statuses.map(s => <option key={s} value={s}>{label(s)}</option>)}</select></label><label><span>Priority</span><select aria-label="Filter priority" value={priority} onChange={e => setPriority(e.target.value)}><option value="">All priorities</option>{priorities.map(p => <option key={p} value={p}>{label(p)}</option>)}</select></label></div>
        <p className="list-count" role="status">{items.length} of {data.tickets.length} demo tickets</p>
        <ul className="conversation-list">{items.map((t,i) => <li key={t.id}><Link href={`/demo/tickets/${t.id}`} aria-current={ticket?.id === t.id ? "true" : undefined} aria-label={t.title}><div className="conversation-meta"><span className={`conversation-avatar tone-${i % 3}`}>{t.customer.slice(0,1)}</span><span>{t.customer.split(" ·")[0]}</span><span className="demo-priority" data-priority={t.priority}>{label(t.priority)}</span></div><strong>{t.title}</strong><p>{t.body}</p><div className="conversation-footer"><span>{t.category}</span><span className={`ticket-badge ticket-badge-${t.status}`}>{label(t.status)}</span></div></Link></li>)}</ul>
        {!items.length && <div className="inbox-empty"><Icon name="inbox" /><h2>No matching demo tickets</h2><p>Try a different search or filter.</p><button className="subtle-button" onClick={() => { setSearch(""); setStatus(""); setPriority(""); }}>Clear filters</button></div>}
      </section>
      {ticket ? <>
        <section className="conversation-panel" aria-label="Selected conversation"><Link className="mobile-back" href="/demo/tickets">← All conversations</Link><header className="conversation-heading"><span className="eyebrow">{ticket.id.startsWith("local-") ? "YOUR TEMPORARY REQUEST" : "SYNTHETIC CONVERSATION"}</span><h2>{ticket.title}</h2><span className={`ticket-badge ticket-badge-${ticket.status}`}>{label(ticket.status)}</span></header>
          <div className="conversation-body"><div className="message-origin"><span className="conversation-avatar">{ticket.customer.slice(0,1)}</span><div><strong>{ticket.customer.split(" ·")[0]}</strong><small>Synthetic customer · example message</small></div><span aria-hidden="true">↙</span></div><p className="message-bubble">{ticket.body}</p>
            <div className="conversation-divider"><span>Internal workspace</span></div>
            {ticket.notes.length ? ticket.notes.map((note,i) => <div className="internal-message" key={i}><span className="eyebrow">YOUR LOCAL NOTE</span><p className="demo-note">{note}</p></div>) : <p className="quiet-message">Only your team sees internal notes. In this demo, everything stays in your browser tab.</p>}
            <form className="note-composer" onSubmit={e => { e.preventDefault(); const form=e.currentTarget; dispatch({ type:"note", id:ticket.id, value:String(new FormData(form).get("note") ?? "") }); form.reset(); }}><label>Add a synthetic internal note<textarea name="note" required maxLength={500} rows={4} placeholder="Add context for the next person…" /></label><div><span>Local note · nothing is sent</span><button className="action-button">Add local note <span aria-hidden="true">↗</span></button></div></form>
          </div>
          <details className="conversation-history"><summary>Activity history <span>{ticket.activity.length} events</span></summary><ol className="demo-activity">{ticket.activity.map((event,i)=><li key={i}>{event}</li>)}</ol><p className="field-help">Example timeline: October 2026. Visitor changes use the demo observation time.</p></details>
        </section>
        <aside className="intelligence-panel" aria-label="Ticket intelligence"><div className="intelligence-heading"><Icon name="spark" /><h2>Intelligence</h2><span className="role-badge">EXAMPLE</span></div><p className="field-help">Authored context, not live inference.</p>
          <section><span className="eyebrow">TRIAGE</span><h3>{ticket.category}</h3><span className="demo-priority" data-priority={ticket.priority}>{label(ticket.priority)} priority</span></section>
          <section className="intelligence-controls"><label>Status<select aria-label="Status" value={ticket.status} onChange={e=>dispatch({type:"status",id:ticket.id,value:e.target.value as Status})}>{statuses.map(s=><option key={s} value={s}>{label(s)}</option>)}</select></label><label>Assigned to<select aria-label="Assigned to" value={ticket.assignee} onChange={e=>dispatch({type:"assign",id:ticket.id,value:e.target.value})}>{agents.map(a=><option key={a}>{a}</option>)}</select></label></section>
          <section><span className="eyebrow">EVIDENCE & NEXT STEP</span>{scenario ? <><h3>{scenario.abstained ? "Needs a human perspective" : "A draft with context"}</h3><p>{scenario.abstained ? "This example has insufficient evidence or needs specialist review." : `${scenario.evidence.length} source reference${scenario.evidence.length===1?"":"s"} support the original example.`}</p><Link className="intelligence-cta" href={`/demo/workflows/${scenario.id}`}>Inspect original workflow example <span aria-hidden="true">↗</span></Link><p className="field-help">Local ticket edits do not regenerate the immutable example.</p></> : <><h3>Make it your own</h3><p>This ticket has no precomputed draft. No classifier or model runs on visitor content.</p><Link href="/demo/workflows">Explore authored workflows ↗</Link></>}</section>
        </aside>
      </> : <section className="conversation-panel inbox-welcome"><Icon name="inbox" width="48" height="48" /><h2>A clear inbox. A fresh perspective.</h2><p>Adjust your filters to find a synthetic conversation.</p></section>}
    </div>
    {creating && <CreateTicket dispatch={dispatch} close={()=>setCreating(false)} />}
  </div>;
}
function CreateTicket({dispatch,close}:{dispatch:(a:Action)=>void;close:()=>void}) {
  const {ref, containFocus}=useModalDialog('input[name="title"]');
  return <dialog ref={ref} onKeyDown={containFocus} className="ticket-create-dialog" aria-labelledby="create-ticket-title" onCancel={e=>{e.preventDefault();close()}}><div className="command-heading"><h2 id="create-ticket-title">A new conversation</h2><button className="icon-button" aria-label="Close ticket form" onClick={close}>×</button></div><p>Synthetic content only. Stored in this tab, with a maximum of 20 temporary tickets.</p><form className="demo-form" aria-label="Create demo ticket" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);dispatch({type:"create",title:String(f.get("title")),body:String(f.get("body")),priority:String(f.get("priority")) as Priority});close();}}><label>Ticket title<input name="title" required maxLength={120} /></label><label>Customer request<textarea name="body" required maxLength={1200} rows={4}/></label><label>Priority<select name="priority" defaultValue="medium">{priorities.map(p=><option key={p} value={p}>{label(p)}</option>)}</select></label><button className="action-button">Save demo ticket</button></form></dialog>;
}
