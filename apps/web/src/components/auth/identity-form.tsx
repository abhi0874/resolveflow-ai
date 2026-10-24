"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { api, ApiError, errorMessage } from "@/lib/session-api";
import { PasswordField } from "./password-field";

type Mode = "verify" | "reset" | "forgot" | "resend";
export function IdentityForm({ mode }: { mode: Mode }) {
  const token = useRef("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const confirming = mode === "verify" || mode === "reset";
  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "";
    // Preserve only in component memory; remove from history before any mutation.
    if (fragment) token.current = /^[A-Za-z0-9_-]{43}$/.test(fragment) ? fragment : "";
    if (window.location.hash) window.history.replaceState(null, "", window.location.pathname);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setPending(true); setError(""); setMessage("");
    try {
      if (confirming && !token.current) throw new ApiError(400, "identity_link_invalid");
      if (mode === "reset" && data.get("password") !== data.get("password_confirmation")) {
        setError("Passwords must match."); return;
      }
      const action = mode === "verify" || mode === "resend" ? "verification" : "password";
      await api(`/auth/${action}/${confirming ? "confirm" : "request"}`, "POST", confirming ? {
        token: token.current, password: String(data.get("password")),
        ...(mode === "reset" ? { password_confirmation: String(data.get("password_confirmation")) } : {}),
      } : { email: String(data.get("email")).trim() });
      if (confirming) {
        token.current = ""; form.reset();
        setMessage(mode === "verify" ? "Email verified. Sign in to continue." : "Password updated. Your previous sessions have been signed out. Sign in with your new password.");
      } else setMessage("If the account is eligible, an email will arrive. Check your inbox and spam folder.");
    } catch (failure) {
      setError(failure instanceof ApiError && failure.status === 400
        ? "This link is invalid, expired or already used, or the password is incorrect. Request a new link or recover your account."
        : errorMessage(failure, true));
    } finally { setPending(false); }
  }

  const title = { verify: "Verify your email", reset: "Choose a new password", forgot: "Recover your account", resend: "Check your email" }[mode];
  const action = { verify: "Verify email", reset: "Reset password", forgot: "Send recovery email", resend: "Resend verification email" }[mode];
  return <form className="auth-form" onSubmit={submit} aria-busy={pending}>
    <h3>{title}</h3>
    <p className="field-help">{mode === "verify" ? "Enter the password you chose when registering. If you did not create this account, use account recovery instead." : mode === "resend" ? "Open the verification link in your inbox. You can request another email below." : "Links expire and can be used once. Your workspace permissions will not change."}</p>
    {!confirming && <div className="form-field"><label htmlFor="email">Email address</label><input id="email" name="email" type="email" autoComplete="email" required maxLength={320} /></div>}
    {confirming && <PasswordField name="password" label={mode === "reset" ? "New password" : "Password"} register={mode === "reset"} />}
    {mode === "reset" && <><p className="field-help" id="password-help">Use 15–128 characters.</p><PasswordField name="password_confirmation" label="Confirm password" register /></>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {message && <p role="status">{message}</p>}
    <button className="action-button" type="submit" disabled={pending || (confirming && !!message)}>{pending ? "Please wait…" : action}</button>
    <p className="form-switch"><Link href="/login">Sign in</Link> · <Link href={mode === "verify" || mode === "resend" ? "/forgot-password" : "/verification-required"}>{mode === "verify" || mode === "resend" ? "Recover account" : "Resend verification"}</Link></p>
  </form>;
}
