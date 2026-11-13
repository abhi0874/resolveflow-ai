"use client";
import Link from "next/link";
import { useState } from "react";
import { Icon } from "@/components/ui/icon";
const examples = [
  { title:"Can I request a refund?", category:"Billing", excerpt:"I purchased my first subscription eight days ago. What is the refund process?", source:"Refund Policy", quote:"Customers may request a refund within 14 days of an initial subscription purchase.", draft:"Your purchase is within the policy’s 14-day request window. A support specialist still needs to verify eligibility before approval.", route:"billing" },
  { title:"Password reset link expired", category:"Account access", excerpt:"My password-reset link expired. How can I get back into my account?", source:"Account Recovery Guide", quote:"Never share a password or recovery code with support.", draft:"Request a fresh password-reset link and use it promptly. Keep your password and recovery codes private.", route:"account" },
];
export function WorkflowOverview() {
  const [selected,setSelected]=useState(0);const example=examples[selected];
  return <div className="showcase-stage"><div className="showcase-frame">
    <div className="showcase-windowbar"><span className="window-dots" aria-hidden="true"><i/><i/><i/></span><span>resolveflow / a workspace with perspective</span><span className="showcase-synthetic">SYNTHETIC PREVIEW</span></div>
    <div className="showcase-app"><div className="showcase-rail" aria-hidden="true"><Icon name="workflow"/><Icon name="overview"/><Icon name="inbox"/><Icon name="book"/><Icon name="chart"/></div>
    <div className="showcase-list"><div className="showcase-label">Your inbox <span>02</span></div><h3>Clarity starts here.</h3><p>Choose a request to explore.</p><div role="group" aria-label="Product preview examples">{examples.map((e,i)=><button key={e.route} aria-pressed={i===selected} onClick={()=>setSelected(i)}><span><span className="small-dot"/> {e.category}</span><strong>{e.title}</strong><small>Authored example <span aria-hidden="true">↗</span></small></button>)}</div><Link href="/demo/tickets">Open the full inbox ↗</Link></div>
    <div className="showcase-conversation" key={example.route}><div className="showcase-conversation-top"><span className="eyebrow">FROM A QUESTION</span><span>→</span></div><h3>{example.title}</h3><p className="showcase-message">{example.excerpt}</p><div className="showcase-flow" aria-label="Illustrated workflow stages">{["Classify","Retrieve","Draft","Review"].map((s,i)=><span key={s} className={i===3?"current":""}><i>{i<3?"✓":i+1}</i>{s}</span>)}</div><div className="showcase-draft"><span className="eyebrow"><Icon name="spark" width="16"/> TO A CONSIDERED DRAFT</span><p>{example.draft}</p></div><div className="showcase-bottom"><span><i className="small-dot"/> Human approval required</span><Link href={`/demo/workflows/${example.route}`}>Inspect this workflow ↗</Link></div></div>
    <div className="showcase-source"><span className="source-stamp"><Icon name="book"/></span><span className="eyebrow">CONTEXT, CONNECTED</span><h3>{example.source}</h3><blockquote>{example.quote}</blockquote><span className="source-caption">Authored illustration.<br/>Inspect full sources in the demo.</span><div className="showcase-source-note"><Icon name="review"/><p>Nothing is sent without a human decision.</p></div></div>
    </div></div><p className="showcase-disclosure">Try the example selector above. Hosted interactions are synthetic and precomputed; the real AI/ML application runs separately.</p></div>;
}
