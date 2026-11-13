"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useModalDialog } from "@/components/ui/use-modal-dialog";
import { Icon } from "@/components/ui/icon";
import type { DemoData } from "@/lib/demo/types";

export function CommandMenu({ data, shortcut = true, onNavigate }: { data: DemoData; shortcut?: boolean; onNavigate?: () => void }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!shortcut) return;
    function key(event: KeyboardEvent) { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setOpen(v => !v); } }
    window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key);
  }, [shortcut]);
  return <><button className="command-trigger" onClick={() => setOpen(true)} aria-label="Search workspace"><Icon name="search" width="17" height="17" /><span>Find anything…</span><kbd>⌘ K</kbd></button>{open && <CommandDialog data={data} close={() => setOpen(false)} onNavigate={onNavigate} />}</>;
}
function CommandDialog({ data, close, onNavigate }: { data: DemoData; close: () => void; onNavigate?: () => void }) {
  const {ref, containFocus} = useModalDialog("input");
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const entries = [
    ...[["Overview", "/demo"], ["Ticket inbox", "/demo/tickets"], ["Knowledge base", "/demo/knowledge"], ["AI workflows", "/demo/workflows"], ["Analytics", "/demo/analytics"], ["Under the hood", "/demo/architecture"]].map(([title, href]) => ({ title, href, kind: "Navigate" })),
    ...data.tickets.map(t => ({ title: t.title, href: `/demo/tickets/${t.id}`, kind: "Ticket" })),
    ...data.documents.map(d => ({ title: d.title, href: `/demo/knowledge/${d.id}`, kind: "Source" })),
  ].filter(e => `${e.title} ${e.kind}`.toLowerCase().includes(query.toLowerCase())).slice(0, 10);

  useEffect(() => {
    ref.current?.querySelector<HTMLElement>(`[data-result="${index}"]`)?.scrollIntoView({ block: "nearest" });
  }, [index, query, ref]);
  return <dialog ref={ref} className="command-dialog" aria-labelledby="command-title" onCancel={e => { e.preventDefault(); close(); }} onKeyDown={e => {
    containFocus(e);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); setIndex(i => entries.length ? (i + (e.key === "ArrowDown" ? 1 : -1) + entries.length) % entries.length : 0); }
    if (e.key === "Enter" && e.target instanceof HTMLInputElement) { e.preventDefault(); ref.current?.querySelector<HTMLAnchorElement>(`[data-result="${index}"]`)?.click(); }
  }}>
    <div className="command-heading"><h2 id="command-title">Where would you like to go?</h2><button className="icon-button" aria-label="Close workspace search" onClick={close}>×</button></div>
    <label className="command-input"><Icon name="search" /><span className="sr-only">Search pages, tickets and sources</span><input value={query} maxLength={120} onChange={e => { setQuery(e.target.value); setIndex(0); }} placeholder="A page, ticket, or source…" aria-describedby="command-help" /></label>
    <div className="command-results" aria-label="Search results">{entries.map((entry, i) => <Link data-result={i} data-active={i === index} href={entry.href} key={entry.href} onClick={() => { close(); onNavigate?.(); }}><span><small>{entry.kind}</small>{entry.title}</span><span aria-hidden="true">↗</span></Link>)}{!entries.length && <p role="status">No matches. Try “refund”, “workflow” or “analytics”.</p>}</div>
    {entries.length > 0 && <p className="sr-only" role="status">{entries.length} results. Selected: {entries[index]?.title}.</p>}
    <p className="command-help" id="command-help">↑ ↓ to choose · Enter to open · Esc to close. Searches synthetic examples only.</p>
  </dialog>;
}
