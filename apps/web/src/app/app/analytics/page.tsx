import Link from "next/link";
import { redirect } from "next/navigation";
import { serverGet } from "@/lib/server-api";
import type { User, Workspace } from "@/lib/session-api";
import { AppShell } from "@/components/workspaces/app-shell";
import { AnalyticsDashboard } from "@/components/analytics/dashboard";
export const dynamic = "force-dynamic";
export const metadata = { title: "Analytics · ResolveFlow AI", robots: { index: false, follow: false } };
export default async function Page({ searchParams }: { searchParams: Promise<{ workspace?: string }> }) {
  let identity: Response | null = null; let spaces: Response | null = null;
  try { [identity, spaces] = await Promise.all([serverGet("/auth/me"), serverGet("/workspaces")]); } catch { /* Safe unavailable state below. */ }
  if (identity?.status === 401 || spaces?.status === 401) redirect("/login");
  if (!identity?.ok || !spaces?.ok) return <main className="service-unavailable"><h1>Analytics unavailable</h1><p>Refresh when the workspace service is available.</p><Link href="/app">Go to workspaces</Link></main>;
  const user: User = await identity.json(); const workspaces: Workspace[] = await spaces.json();
  const requested = (await searchParams).workspace;
  const selected = requested ? workspaces.find(w => w.id === requested) : workspaces[0];
  if (!selected) return <main className="service-unavailable"><h1>Choose an accessible workspace</h1><Link href="/app">Go to workspaces</Link></main>;
  return <AppShell user={user} workspaces={workspaces} selected={selected} area="analytics">
    {selected.permissions.includes("analytics:read") ? <AnalyticsDashboard key={selected.id} workspaceId={selected.id} /> : <section className="workspace-card"><h1>Analytics access restricted</h1><p>Workspace owners and admins can view analytics.</p></section>}
  </AppShell>;
}
