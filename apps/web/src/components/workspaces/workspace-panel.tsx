"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { AcceptInvitation, PendingInvitations } from "./invitations";
import {
  api,
  errorMessage,
  type User,
  type Workspace,
  type Member,
  type Role,
} from "@/lib/session-api";

const roleLabels: Record<Role, string> = {
  owner: "Owner",
  admin: "Admin",
  support_agent: "Support agent",
  viewer: "Viewer",
};

export function WorkspacePanel({
  user,
  workspaces,
  selected,
  initialMembers,
}: {
  user: User;
  workspaces: Workspace[];
  selected?: Workspace;
  initialMembers: Member[];
}) {
  const router = useRouter();
  const [creating, setCreating] = useState(!workspaces.length);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function perform(action: () => Promise<void>) {
    setError("");
    setNotice("");
    setPending(true);
    try {
      await action();
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setPending(false);
    }
  }
  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void perform(async () => {
      const created = await api<Workspace>("/workspaces", "POST", {
        name: data.get("name"),
        slug: data.get("slug"),
      });
      setCreating(false);
      router.push(`/app?workspace=${created.id}`);
      router.refresh();
    });
  }
  function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void perform(async () => {
      await api(`/workspaces/${selected!.id}`, "PATCH", {
        name: data.get("name"),
        slug: data.get("slug"),
      });
      setNotice("Workspace settings saved.");
      router.refresh();
    });
  }
  const manage = selected?.permissions.includes("workspace:members");
  const settings = selected?.permissions.includes("workspace:settings");
  return (
    <main className="workspace-page" id="main-content">
      <aside className="workspace-sidebar">
        <Link href="/" className="brand">
          ResolveFlow <span className="brand-ai">AI</span>
        </Link>
        <div className="workspace-navigation">
          <span className="eyebrow">YOUR WORKSPACES</span>
          <nav aria-label="Workspaces">
            {workspaces.map((workspace) => (
              <Link
                key={workspace.id}
                href={`/app?workspace=${workspace.id}`}
                aria-current={
                  selected?.id === workspace.id ? "page" : undefined
                }
                onClick={() => setCreating(false)}
              >
                <span className="workspace-avatar" aria-hidden="true">
                  {workspace.name.slice(0, 1).toUpperCase()}
                </span>
                <span>
                  {workspace.name}
                  <small>{roleLabels[workspace.role]}</small>
                </span>
              </Link>
            ))}
          </nav>
          <button
            className="subtle-button"
            onClick={() => {
              setCreating(true);
              setError("");
            }}
          >
            ＋ Create workspace
          </button>
        </div>
        <div className="workspace-account">
          <span className="eyebrow">SIGNED IN AS</span>
          <p>{user.email}</p>
          {!user.email_verified && <p className="field-help">Email is unverified. <Link href="/verification-required">Verify email</Link></p>}
          <button
            className="subtle-button"
            disabled={pending}
            onClick={() =>
              void perform(async () => {
                await api("/auth/logout", "POST");
                window.location.replace("/login");
              })
            }
          >
            Sign out ↗
          </button>
        </div>
      </aside>
      <section className="workspace-content" aria-busy={pending}>
        <header className="workspace-heading">
          <div>
            <span className="eyebrow">
              WORKSPACE / {creating ? "GET STARTED" : "OVERVIEW"}
            </span>
            <h1>
              {creating
                ? "A home for your team."
                : (selected?.name ?? "Select a workspace.")}
            </h1>
            <p>
              {creating
                ? "Bring the right people together in one shared space."
                : "Your team, your settings, your shared foundation."}
            </p>
          </div>
          {selected && !creating ? (
            <span className="role-badge">{roleLabels[selected.role]}</span>
          ) : null}
        </header>
        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}
        {notice ? (
          <p className="success-message" role="status">
            {notice}
          </p>
        ) : null}
        <AcceptInvitation verified={user.email_verified} />
        {creating ? (
          <section className="workspace-card create-card">
            <span className="eyebrow">NEW WORKSPACE</span>
            <h2>Make it yours.</h2>
            <form onSubmit={create} className="auth-form">
              <WorkspaceFields />
              <p className="field-help">
                You’ll be the owner. You can invite registered teammates after
                creating the workspace.
              </p>
              <button className="action-button" disabled={pending}>
                {pending ? "Creating…" : "Create workspace"}
                <span aria-hidden="true">↗</span>
              </button>
              {selected ? (
                <button
                  type="button"
                  className="subtle-button"
                  onClick={() => setCreating(false)}
                >
                  Cancel
                </button>
              ) : null}
            </form>
          </section>
        ) : selected ? (
          <>
            <section className="workspace-welcome">
              <span className="eyebrow">A STRONG START</span>
              <h2>Good work begins with the right people.</h2>
              <p>
                Manage your team and workspace here. Open the ticket inbox to
                organize requests and collaborate with your team.
              </p>
              <Link
                className="primary-link"
                href={`/app/tickets?workspace=${selected.id}`}
              >
                Open ticket inbox ↗
              </Link>
              <Link
                className="primary-link"
                href={`/app/knowledge-base?workspace=${selected.id}`}
              >
                Knowledge base ↗
              </Link>
              {selected.permissions.includes("analytics:read") && <Link className="primary-link" href={`/app/analytics?workspace=${selected.id}`}>Workspace analytics ↗</Link>}
              <div className="workspace-stats">
                <span>
                  <strong>{initialMembers.length}</strong> Team members
                </span>
                <span>
                  <strong>{roleLabels[selected.role]}</strong> Your access
                </span>
              </div>
            </section>
            <section className="workspace-card">
              <div className="card-heading">
                <div>
                  <span className="eyebrow">PEOPLE & ACCESS</span>
                  <h2>Your team</h2>
                </div>
                <span className="role-badge">
                  {initialMembers.length} members
                </span>
              </div>
              <p className="field-help">
                Owners manage ownership. Admins manage support agents and
                viewers.
              </p>
              <ul className="member-list">
                {initialMembers.map((member) => (
                  <li key={member.user_id}>
                    <div className="member-identity">
                      <span className="workspace-avatar" aria-hidden="true">
                        {member.email[0].toUpperCase()}
                      </span>
                      <div>
                        {member.email}
                        {member.user_id === user.id ? <small>You</small> : null}
                      </div>
                    </div>
                    {manage &&
                    (selected.role === "owner" ||
                      ["viewer", "support_agent"].includes(member.role)) ? (
                      <div className="member-actions">
                        <select
                          aria-label={`Role for ${member.email}`}
                          value={member.role}
                          disabled={pending}
                          onChange={(event) => {
                            const role = event.target.value;
                            void perform(async () => {
                              await api(
                                `/workspaces/${selected.id}/members/${member.user_id}`,
                                "PATCH",
                                { role },
                              );
                              setNotice("Member role updated.");
                              router.refresh();
                            });
                          }}
                        >
                          {(selected.role === "owner"
                            ? (Object.keys(roleLabels) as Role[])
                            : (["support_agent", "viewer"] as Role[])
                          ).map((role) => (
                            <option key={role} value={role}>
                              {roleLabels[role]}
                            </option>
                          ))}
                        </select>
                        <button
                          className="subtle-button danger-button"
                          disabled={pending}
                          aria-label={`Remove ${member.email}`}
                          onClick={() => {
                            if (
                              window.confirm(
                                `Remove ${member.email} from this workspace?`,
                              )
                            )
                              void perform(async () => {
                                await api(
                                  `/workspaces/${selected.id}/members/${member.user_id}`,
                                  "DELETE",
                                );
                                setNotice("Member removed.");
                                router.refresh();
                              });
                          }}
                        >
                          Remove
                        </button>
                      </div>
                    ) : (
                      <span className="role-badge">
                        {roleLabels[member.role]}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
              {manage ? (
                <AddMember
                  owner={selected.role === "owner"}
                  pending={pending}
                  onAdd={(data) =>
                    perform(async () => {
                      await api(
                        `/workspaces/${selected.id}/invitations`,
                        "POST",
                        data,
                      );
                      setNotice("Invitation created. Access begins only after the recipient accepts.");
                      router.refresh();
                    })
                  }
                />
              ) : (
                <p className="field-help">
                  Your role can view this team. Ask an owner or admin to change
                  access.
                </p>
              )}
              {manage && <PendingInvitations key={selected.id} workspace={selected} refresh={notice} />}
            </section>
            <section className="workspace-card">
              <span className="eyebrow">WORKSPACE DETAILS</span>
              <h2>Settings</h2>
              {settings ? (
                <form
                  className="auth-form settings-form"
                  onSubmit={saveSettings}
                >
                  <WorkspaceFields workspace={selected} />
                  <button className="action-button" disabled={pending}>
                    Save changes
                  </button>
                </form>
              ) : (
                <dl className="workspace-details">
                  <dt>Name</dt>
                  <dd>{selected.name}</dd>
                  <dt>Slug</dt>
                  <dd>{selected.slug}</dd>
                </dl>
              )}
            </section>
          </>
        ) : (
          <p>
            Select one of your workspaces from the navigation, or create a new
            one.
          </p>
        )}
      </section>
    </main>
  );
}

function WorkspaceFields({ workspace }: { workspace?: Workspace }) {
  return (
    <>
      <div className="form-field">
        <label htmlFor="workspace-name">Workspace name</label>
        <input
          id="workspace-name"
          name="name"
          required
          maxLength={120}
          defaultValue={workspace?.name}
          placeholder="e.g. Customer Care"
        />
      </div>
      <div className="form-field">
        <label htmlFor="workspace-slug">Workspace slug</label>
        <input
          id="workspace-slug"
          name="slug"
          required
          maxLength={80}
          pattern="[a-z0-9]+(-[a-z0-9]+)*"
          defaultValue={workspace?.slug}
          placeholder="e.g. customer-care"
          aria-describedby="slug-help"
        />
        <p className="field-help" id="slug-help">
          A unique name using lowercase letters, numbers, and hyphens.
        </p>
      </div>
    </>
  );
}

function AddMember({
  owner,
  pending,
  onAdd,
}: {
  owner: boolean;
  pending: boolean;
  onAdd: (data: { email: string; role: string }) => Promise<void>;
}) {
  return (
    <form
      className="add-member-form"
      onSubmit={(event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const data = new FormData(form);
        void onAdd({
          email: String(data.get("email")),
          role: String(data.get("role")),
        });
      }}
    >
      <div className="form-field">
        <label htmlFor="member-email">Invite a registered teammate</label>
        <input
          id="member-email"
          name="email"
          type="email"
          required
          maxLength={320}
          placeholder="teammate@company.com"
        />
      </div>
      <div className="form-field">
        <label htmlFor="member-role">Role</label>
        <select id="member-role" name="role" defaultValue="viewer">
          {(owner
            ? (Object.keys(roleLabels) as Role[])
            : (["support_agent", "viewer"] as Role[])
          ).map((role) => (
            <option key={role} value={role}>
              {roleLabels[role]}
            </option>
          ))}
        </select>
      </div>
      <button className="action-button" disabled={pending}>
        Send invitation
      </button>
    </form>
  );
}
