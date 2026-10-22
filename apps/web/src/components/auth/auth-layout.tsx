import Link from "next/link";
import type { ReactNode } from "react";

export function AuthLayout({
  register = false,
  children,
}: {
  register?: boolean;
  children: ReactNode;
}) {
  return (
    <main className="auth-page" id="main-content">
      <section className="auth-story">
        <Link href="/" className="brand">
          ResolveFlow <span className="brand-ai">AI</span>
        </Link>
        <div>
          <span className="eyebrow">YOUR TEAM. ONE SHARED SPACE.</span>
          <h1>
            Great support
            <br />
            starts with
            <br />
            <em>connection.</em>
          </h1>
          <p>
            A dedicated home for your team, with the right access for every
            member.
          </p>
        </div>
        <div className="auth-story-footer">
          <span className="small-dot" /> Built for thoughtful support teams.
        </div>
      </section>
      <section className="auth-entry">
        <Link href="/" className="back-link">
          ← Back to ResolveFlow
        </Link>
        <div className="auth-card">
          <span className="eyebrow">
            {register ? "A FRESH START" : "WELCOME BACK"}
          </span>
          <h2>
            {register ? "Make room for your team." : "Your workspace awaits."}
          </h2>
          <p>
            {register
              ? "Create your account, then bring your team together."
              : "Sign in to continue to your workspaces."}
          </p>
          {children}
        </div>
        <p className="auth-footnote">A calmer place to work together.</p>
      </section>
    </main>
  );
}
