"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError } from "@/lib/session-api";
import { settingsError } from "./account-settings";
import styles from "@/app/app/settings/account/settings.module.css";

export function EmailProof({ action }: { action: "approve" | "confirm" }) {
  const token = useRef("");
  const [pending, setPending] = useState(false);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const value = new URLSearchParams(window.location.hash.slice(1)).get("token");
    if (value && /^[A-Za-z0-9_-]{43}$/.test(value)) token.current = value;
    if (window.location.hash) window.history.replaceState(null, "", window.location.pathname);
  }, []);

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token.current) {
      setError("This link cannot be used. Request a new email change.");
      return;
    }
    setPending(true);
    setError("");
    try {
      await api("/account/email/confirm", "POST", { token: token.current, action });
      token.current = "";
      setFinished(true);
    } catch (failure) {
      setError(failure instanceof ApiError && failure.status === 400
        ? "This link cannot be used. Request a new email change."
        : settingsError(failure));
    } finally {
      setPending(false);
    }
  }

  const approval = action === "approve";
  return <form className={`auth-card auth-form ${styles.card}`} onSubmit={confirm} aria-busy={pending}>
    <h1>{approval ? "Approve email change" : "Verify your new email"}</h1>
    <p>Use the browser where you requested the change.</p>
    {error && <p role="alert" className="form-error">{error}</p>}
    {finished ? <p role="status">{approval
      ? "Approval recorded. Open the verification link in your new inbox."
      : "Email updated. All sessions have been signed out."}</p> :
      <button className="action-button" disabled={pending}>{pending ? "Please wait…" : approval ? "Approve change" : "Verify new email"}</button>}
    <Link href={finished && !approval ? "/login" : "/app/settings/account"}>
      {finished && !approval ? "Sign in again" : "Return to personal settings"}
    </Link>
  </form>;
}
