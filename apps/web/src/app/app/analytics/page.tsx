import Link from "next/link";
import { workspaceAccess } from "@/lib/workspace-access";
import { AppShell } from "@/components/workspaces/app-shell";
import { AnalyticsDashboard } from "@/components/analytics/dashboard";
export const dynamic = "force-dynamic";
export const metadata = { title: "Analytics · ResolveFlow AI", robots: { index: false, follow: false } };
export default async function Page({ searchParams }: { searchParams: Promise<{ workspace?: string }> }) {
  const access = await workspaceAccess();
  if (!access) return <main className="service-unavailable"><h1>Analytics unavailable</h1><p>Refresh when the workspace service is available.</p><Link href="/app">Go to workspaces</Link></main>;
  const { user, workspaces } = access;
  const requested = (await searchParams).workspace;
  const selected = requested ? workspaces.find(w => w.id === requested) : workspaces[0];
  if (!selected) return <main className="service-unavailable"><h1>Choose an accessible workspace</h1><Link href="/app">Go to workspaces</Link></main>;
  return <AppShell user={user} workspaces={workspaces} selected={selected} area="analytics">
    {selected.permissions.includes("analytics:read") ? <AnalyticsDashboard key={selected.id} workspaceId={selected.id} /> : <section className="workspace-card"><h1>Analytics access restricted</h1><p>Workspace owners and admins can view analytics.</p></section>}
  </AppShell>;
}
