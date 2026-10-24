"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Role, type Workspace } from "@/lib/session-api";

export function AcceptInvitation({ verified }: { verified: boolean }) {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  return <section className="workspace-card">
    <h2>Join an invited team</h2>
    <p>{verified ? "Your address has been confirmed." : "Your email address has not been verified."} An invitation grants access only after you accept it while signed in to the invited account.</p>
    <form className="auth-form" onSubmit={async event => {
      event.preventDefault(); setPending(true); setError("");
      try {
        const workspace = await api<Workspace>("/auth/invitations/accept", "POST", { token });
        setToken(""); router.push(`/app?workspace=${workspace.id}`); router.refresh();
      } catch { setError("Invitation could not be accepted. Check the code, invited account and expiry, or request a new invitation."); }
      finally { setPending(false); }
    }}>
      <div className="form-field"><label htmlFor="invitation-code">Invitation code</label>
        <input id="invitation-code" type="password" autoComplete="off" required minLength={43} maxLength={43} value={token} onChange={event => setToken(event.target.value)} />
      </div>
      <button className="action-button" disabled={pending}>{pending ? "Accepting…" : "Accept invitation"}</button>
      {error && <p className="form-error" role="alert">{error}</p>}
    </form>
  </section>;
}

type Invitation = { id: string; email: string; role: Role; expires_at: string };

export function PendingInvitations({ workspace, refresh }: { workspace: Workspace; refresh: string }) {
  const [items, setItems] = useState<Invitation[]>([]);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    let active = true;
    api<Invitation[]>(`/workspaces/${workspace.id}/invitations`).then(value => {
      if (active) { setItems(value); setError(""); }
    }).catch(() => { if (active) setError("Pending invitations are unavailable."); });
    return () => { active = false; };
  }, [workspace.id, refresh, revision]);
  return <section aria-label="Pending invitations">
    <h3>Pending invitations</h3>
    {error ? <p role="alert">{error}</p> : <ul className="member-list">{items.map(item => <li key={item.id}>
      <span>{item.email} · {item.role.replace("_", " ")} · expires {new Date(item.expires_at).toLocaleDateString()}</span>
      {(workspace.role === "owner" || ["viewer", "support_agent"].includes(item.role)) && <button className="subtle-button" disabled={pending} aria-label={`Revoke invitation for ${item.email}`} onClick={async () => {
        setPending(true); setError("");
        try { await api(`/workspaces/${workspace.id}/invitations/${item.id}`, "DELETE"); setRevision(value => value + 1); }
        catch { setError("Invitation could not be revoked. Refresh and try again."); }
        finally { setPending(false); }
      }}>Revoke</button>}
    </li>)}</ul>}
    {!error && items.length === 0 && <p>No pending invitations.</p>}
    <button className="subtle-button" disabled={pending} onClick={() => setRevision(value => value + 1)}>Refresh invitations</button>
  </section>;
}
