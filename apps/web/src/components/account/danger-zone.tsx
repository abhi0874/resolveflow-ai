"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/session-api";
import { PasswordField } from "@/components/auth/password-field";
import styles from "@/app/app/settings/account/settings.module.css";

type Impact = { empty_workspaces: string[]; blocked_workspaces: string[] };

export function DangerZone({ password }: { password: boolean }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [impact, setImpact] = useState<Impact | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [challenge, setChallenge] = useState("");
  const verified = Boolean(challenge);
  const [phrase, setPhrase] = useState("");

  async function open(googleReturn = false) {
    setError(""); setPhrase(""); setChallenge(""); setImpact(null);
    dialog.current?.showModal();
    try {
      setImpact(await api<Impact>("/account/deletion/impact"));
      if (googleReturn) setChallenge((await api<{challenge: string}>("/account/deletion/challenge", "POST", {})).challenge);
    }
    catch { setError("Could not check your workspaces. Close this dialog and try again."); }
  }

  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.get("delete") === "confirm") {
      const timer = window.setTimeout(() => {
        url.searchParams.delete("delete");
        window.history.replaceState(null, "", url.pathname + url.search);
        void open(true);
      }, 0);
      return () => window.clearTimeout(timer);
    }
  }, []);

  return <section className={`auth-card auth-form ${styles.card}`}>
    <h2>Danger Zone</h2>
    <p>Permanently delete your ResolveFlow account.</p>
    <button type="button" className="subtle-button" ref={trigger} onClick={() => void open()}>Delete account</button>
    <dialog className={styles.dangerDialog} ref={dialog} aria-labelledby="delete-title"
      onCancel={event => { if (busy) event.preventDefault(); }}
      onClose={() => {
        dialog.current?.querySelector("form")?.reset();
        setChallenge(""); setPhrase(""); trigger.current?.focus();
      }}>
      <form className="auth-form" method="post" aria-busy={busy} onSubmit={async event => {
        event.preventDefault();
        if (busy || !impact || impact.blocked_workspaces.length) return;
        const data = new FormData(event.currentTarget);
        const field = event.currentTarget.elements.namedItem("delete_password");
        if (field instanceof HTMLInputElement) field.value = "";
        setBusy(true); setError("");
        try {
          if (!verified) {
            const result = await api<{verified?: boolean; url?: string}>("/account/deletion/reauthenticate", "POST",
              password ? {current_password: data.get("delete_password")} : {});
            if (result.url) { window.location.assign(result.url); return; }
            if (result.verified) setChallenge((await api<{challenge: string}>("/account/deletion/challenge", "POST", {})).challenge);
          } else {
            const result = await api<{cleanup: string}>("/account/deletion/confirm", "POST", {confirmation: phrase, challenge});
            window.location.replace("/login?deleted=" + (result.cleanup === "complete" ? "yes" : "review"));
          }
        } catch (failure) {
          setChallenge("");
          if (failure instanceof ApiError && failure.code === "workspace_transfer_required") setError("Transfer workspace ownership before deleting your account.");
          else if (failure instanceof ApiError && failure.code === "account_busy") setError("An account operation is still active. Finish or cancel it, then try again.");
          else if (failure instanceof ApiError && failure.code === "deletion_proof_required") { setChallenge(""); setError("Verification expired. Verify again."); }
          else setError("Deletion could not be confirmed. Check your sign-in details and try again.");
        } finally { setBusy(false); }
      }}>
        <h2 id="delete-title">Permanently delete your account?</h2>
        <p>This cannot be undone. Your profile, picture, sign-in methods and sessions will be erased. Your Google account is unaffected.</p>
        <p>Shared workspace files and history stay with the team. Verified personal invitation files are removed. Unattributed files stay private for manual review.</p>
        <p>Existing restricted backups can retain earlier copies until their retention period ends. Deletion does not erase previously delivered email.</p>
        {!impact && !error && <p role="status">Checking your workspaces…</p>}
        {!!impact?.empty_workspaces.length && <p>Empty workspaces to be closed: {impact.empty_workspaces.join(", ")}.</p>}
        {!!impact?.blocked_workspaces.length && <p role="alert">Transfer ownership before continuing: {impact.blocked_workspaces.join(", ")}.</p>}
        {impact && !impact.blocked_workspaces.length && (verified
          ? <label>Type DELETE to confirm<input value={phrase} autoComplete="off" onChange={e => setPhrase(e.target.value)} required /></label>
          : password ? <PasswordField name="delete_password" label="Current password for deletion" />
          : <p>Verify your identity with the linked Google account. Google must confirm a fresh sign-in.</p>)}
        {error && <p role="alert">{error}</p>}
        <button type="button" className="subtle-button" disabled={busy} onClick={() => dialog.current?.close()}>Cancel</button>
        <button className="action-button" disabled={!impact || !!impact.blocked_workspaces.length || busy || (verified && phrase !== "DELETE")}>
          {busy ? "Please wait…" : verified ? "Permanently delete my account" : password ? "Verify password" : "Verify with Google"}
        </button>
      </form>
    </dialog>
  </section>;
}
