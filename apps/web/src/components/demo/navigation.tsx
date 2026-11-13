"use client";
import Link from "next/link";
import { useState } from "react";
import { Icon,type IconName } from "@/components/ui/icon";
import { ThemeSwitcher } from "@/components/ui/theme-switcher";
import { useModalDialog } from "@/components/ui/use-modal-dialog";
import { CommandMenu } from "./command-menu";
import type { DemoData } from "@/lib/demo/types";
export const demoNavigation=[["overview","Overview","overview"],["tickets","Ticket inbox","inbox"],["knowledge","Knowledge base","book"],["workflows","AI workflows","workflow"],["analytics","Analytics","chart"],["architecture","Under the hood","classify"]];
function Navigation({section,close}:{section:string;close?:()=>void}){return <nav className="ticket-nav" aria-label="Demo navigation">{demoNavigation.map(([key,title,icon])=><Link key={key} href={key==="overview"?"/demo":`/demo/${key}`} aria-label={title} aria-current={section===key?"page":undefined} onClick={close}><Icon name={icon as IconName} width="20" height="20"/><span>{title}</span></Link>)}</nav>}
export function WorkspaceNavigation({section,data,onReset}:{section:string;data:DemoData;onReset:()=>void}){
  const [open,setOpen]=useState(false);
  return <><aside className="workspace-sidebar structural-sidebar"><Link href="/" className="rail-brand" aria-label="ResolveFlow AI home"><span className="rail-logo"><Icon name="workflow" width="25"/></span><span>ResolveFlow<small>SUPPORT INTELLIGENCE</small></span></Link><CommandMenu data={data} shortcut={!open}/><div className="rail-nav-title">WORKSPACE</div><Navigation section={section}/><div className="sidebar-bottom"><div className="sidebar-project"><span>N</span><div>Northstar Studio<small>Synthetic workspace</small></div></div><ThemeSwitcher/><button className="rail-reset" onClick={onReset}><span aria-hidden="true">↻</span> Reset demo</button><p>Local changes.<br/>No external actions.</p></div></aside>
  <header className="mobile-workspace-bar"><Link href="/" aria-label="ResolveFlow AI home"><Icon name="workflow"/> ResolveFlow <small>AI</small></Link><button className="icon-button" aria-label="Open navigation" onClick={()=>setOpen(true)}><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg></button></header>{open&&<NavigationDrawer section={section} data={data} close={()=>setOpen(false)} onReset={()=>{setOpen(false);onReset()}}/>}</>;
}
function NavigationDrawer({section,data,close,onReset}:{section:string;data:DemoData;close:()=>void;onReset:()=>void}){
 const {ref, containFocus}=useModalDialog();
 return <dialog ref={ref} onKeyDown={containFocus} className="navigation-drawer" aria-labelledby="navigation-title" onCancel={e=>{e.preventDefault();close()}}><div className="command-heading"><h2 id="navigation-title">Your workspace</h2><button className="icon-button" aria-label="Close navigation" onClick={close}>×</button></div><Navigation section={section} close={close}/><CommandMenu data={data} onNavigate={close}/><ThemeSwitcher/><button className="subtle-button" onClick={onReset}>Reset demo</button><p>Synthetic records. Precomputed workflows. Changes stay in this tab.</p></dialog>;
}
