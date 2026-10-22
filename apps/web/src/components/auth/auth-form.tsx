"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { api, errorMessage } from "@/lib/session-api";
import { PasswordField } from "./password-field";

export function AuthForm({ register = false }: { register?: boolean }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
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
      await api(`/auth/${register ? "register" : "login"}`, "POST", {
        email: String(data.get("email")).trim(),
        password,
        ...(register ? { password_confirmation: confirmation } : {}),
      });
      window.location.replace("/app");
    } catch (error) {
      setError(errorMessage(error, true));
      setPending(false);
    }
  }
  return (
    <form onSubmit={submit} className="auth-form" aria-busy={pending}>
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
      <button className="action-button" disabled={pending} type="submit">
        {pending ? "Please wait…" : register ? "Create account" : "Sign in"}
        <span aria-hidden="true">↗</span>
      </button>
      <p className="form-switch">
        {register ? "Already have an account?" : "New to ResolveFlow?"}{" "}
        <Link href={register ? "/login" : "/register"}>
          {register ? "Sign in" : "Create an account"}
        </Link>
      </p>
      {register ? (
        <p className="field-help">
          Email ownership is not verified yet. Use a development account; email
          invitations and recovery are not available.
        </p>
      ) : null}
    </form>
  );
}
