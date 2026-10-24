"use client";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import {
  api,
  errorMessage,
  type User,
  type Workspace,
} from "@/lib/session-api";
export function AppShell({
  user,
  workspaces,
  selected,
  children,
  area = "tickets",
}: {
  user: User;
  workspaces: Workspace[];
  selected: Workspace;
  children: ReactNode;
  area?: "tickets" | "knowledge-base" | "analytics";
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  return (
    <main className="workspace-page" id="main-content">
      <aside className="workspace-sidebar">
        <Link href="/" className="brand">
          ResolveFlow <span className="brand-ai">AI</span>
        </Link>
        <div className="workspace-navigation">
          <span className="eyebrow">YOUR WORKSPACES</span>
          <nav aria-label="Workspaces">
            {workspaces.map((w) => (
              <Link
                key={w.id}
                href={`/app/${area}?workspace=${w.id}`}
                aria-current={w.id === selected.id ? "page" : undefined}
              >
                <span className="workspace-avatar" aria-hidden="true">
                  {w.name[0].toUpperCase()}
                </span>
                <span>
                  {w.name}
                  <small>{w.role.replace("_", " ")}</small>
                </span>
              </Link>
            ))}
          </nav>
          <nav aria-label="Workspace tools" className="ticket-nav">
            <Link
              href={`/app/tickets?workspace=${selected.id}`}
              aria-current={area === "tickets" ? "page" : undefined}
            >
              ◫ &nbsp; Ticket inbox
            </Link>
            <Link
              href={`/app/knowledge-base?workspace=${selected.id}`}
              aria-current={area === "knowledge-base" ? "page" : undefined}
            >
              ▤ &nbsp; Knowledge base
            </Link>
            {selected.permissions.includes("analytics:read") && <Link href={`/app/analytics?workspace=${selected.id}`} aria-current={area === "analytics" ? "page" : undefined}>◴ &nbsp; Analytics</Link>}
            <Link href={`/app?workspace=${selected.id}`}>
              Team & settings ↗
            </Link>
          </nav>
        </div>
        <div className="workspace-account">
          <span className="eyebrow">SIGNED IN AS</span>
          <p>{user.email}</p>
          {!user.email_verified && <p className="field-help">Email is unverified. <Link href="/verification-required">Verify email</Link></p>}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button
            className="subtle-button"
            disabled={pending}
            onClick={async () => {
              setPending(true);
              try {
                await api("/auth/logout", "POST");
                window.location.replace("/login");
              } catch (e) {
                setError(errorMessage(e));
                setPending(false);
              }
            }}
          >
            Sign out ↗
          </button>
        </div>
      </aside>
      <section className="workspace-content ticket-content">{children}</section>
    </main>
  );
}
