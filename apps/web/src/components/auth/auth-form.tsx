"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { api, ApiError, errorMessage } from "@/lib/session-api";
import { accountEntry } from "@/lib/account-navigation";
import { PasswordField } from "./password-field";

export function AuthForm({ register = false, destination, googleFailed = false }: { register?: boolean; destination: string; googleFailed?: boolean }) {
  const [pending, setPending] = useState(false);
  const googleError = "Google sign-in could not finish. Try again or use your existing sign-in method.";
  const [error, setError] = useState(googleFailed ? googleError : "");
  const [googlePending, setGooglePending] = useState(false);
  async function continueWithGoogle() {
    setGooglePending(true);
    setError("");
    try {
      const result = await api<{ url: string }>("/auth/google/start", "POST", { destination });
      const url = new URL(result.url);
      if (url.origin !== "https://accounts.google.com" || url.pathname !== "/o/oauth2/v2/auth") {
        throw new Error("Unexpected authorization endpoint");
      }
      window.location.assign(url.href);
    } catch (failure) {
      setError(failure instanceof ApiError && failure.status === 503
        ? "Google sign-in is unavailable here. You can use email and password."
        : googleError);
      setGooglePending(false);
    }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password"));
    const confirmation = String(data.get("password_confirmation"));
    setError("");
    if (register && password !== confirmation) {
      setError("Passwords don’t match.");
      return;
    }
    if (register && !password.trim()) {
      setError("Choose a password with at least 15 characters.");
      return;
    }
    setPending(true);
    try {
      const result = await api<{ status?: string }>(`/auth/${register ? "register" : "login"}`, "POST", {
        email: String(data.get("email")).trim(),
        password,
        ...(register ? { password_confirmation: confirmation } : {}),
      });
      window.location.replace(result.status === "accepted" ? "/verification-required" : destination);
    } catch (error) {
      setError(errorMessage(error, true));
      setPending(false);
    }
  }
  return (
    <form onSubmit={submit} className="auth-form" aria-busy={pending || googlePending}>
      <button className="action-button" type="button" disabled={pending || googlePending} onClick={continueWithGoogle}>
        {googlePending ? "Opening Google…" : "Continue with Google"}
      </button>
      <div className="form-field">
        <label htmlFor="email">Email address</label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          required
          maxLength={320}
        />
      </div>
      <PasswordField name="password" label="Password" register={register} />
      {register ? (
        <>
          <p className="field-help" id="password-help">
            Use 15–128 characters. A memorable passphrase works well.
          </p>
          <PasswordField
            name="password_confirmation"
            label="Confirm password"
            register
          />
        </>
      ) : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <button className="action-button" disabled={pending || googlePending} type="submit">
        {pending ? "Please wait…" : register ? "Create account" : "Sign in"}
        <span aria-hidden="true">↗</span>
      </button>
      <p className="form-switch">
        {register ? "Already have an account?" : "New to ResolveFlow?"}{" "}
        <Link href={accountEntry(register ? "/login" : "/register", destination)}>
          {register ? "Sign in" : "Create an account"}
        </Link>
      </p>
      {register ? (
        <p className="field-help">
          Check your inbox for verification when email delivery is configured.
          Local development may allow access before verification.
        </p>
      ) : null}
      {!register && <p className="form-switch"><Link href="/forgot-password">Forgot password?</Link> · <Link href="/verification-required">Verify email</Link></p>}
    </form>
  );
}
