"use client";

import { DangerZone } from "./danger-zone";
import Image from "next/image";
import Link from "next/link";
import { useState, type FormEvent, type ReactNode } from "react";
import { PasswordField } from "@/components/auth/password-field";
import { api, ApiError } from "@/lib/session-api";
import styles from "@/app/app/settings/account/settings.module.css";

export type AccountProfile = {
  display_name: string | null;
  avatar: string | null;
  email: string;
  email_verified: boolean;
  password_enabled: boolean;
  google_linked: boolean;
};

export function settingsError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.code === "current_password_required") return "Enter your current password and try again.";
    if (error.status === 401) return "Your session has expired. Sign in and try again.";
    if (error.status === 403) return "This action could not be authorized. Refresh the page and try again.";
    if (error.status === 422) return "Check the form and try again.";
    if (error.status === 429) return "Too many attempts. Wait 15 minutes before trying again.";
  }
  return "The change could not be saved. Please try again.";
}

class FormError extends Error {}

async function picturePixels(file: File) {
  if (!["image/png", "image/jpeg"].includes(file.type) || file.size > 5 * 1024 * 1024) {
    throw new FormError("Choose a PNG or JPEG under 5 MB.");
  }
  const image = await createImageBitmap(file).catch(() => {
    throw new FormError("This picture could not be opened.");
  });
  try {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 56;
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) throw new FormError("Image processing is unavailable in this browser.");
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, 56, 56);
    const size = Math.min(image.width, image.height);
    context.drawImage(image, (image.width - size) / 2, (image.height - size) / 2, size, size, 0, 0, 56, 56);
    const rgba = context.getImageData(0, 0, 56, 56).data;
    let rgb = "";
    for (let i = 0; i < rgba.length; i += 4) rgb += String.fromCharCode(rgba[i], rgba[i + 1], rgba[i + 2]);
    return btoa(rgb);
  } finally {
    image.close();
  }
}

function SettingsForm({ title, submitLabel, onSave, children }: {
  title: string;
  submitLabel: string;
  onSave: (data: FormData) => Promise<string>;
  children: ReactNode;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    data.forEach((_value, key) => {
      const field = form.elements.namedItem(key);
      if (field instanceof HTMLInputElement && field.autocomplete.includes("password")) field.value = "";
    });
    setPending(true);
    setError("");
    setSuccess("");
    try {
      setSuccess(await onSave(data));
    } catch (failure) {
      setError(failure instanceof FormError ? failure.message : settingsError(failure));
    } finally {
      setPending(false);
    }
  }
  return <form className={`auth-card auth-form ${styles.card}`} aria-label={title} method="post" onSubmit={submit} aria-busy={pending}>
    <h2>{title}</h2>
    {children}
    {error && <p role="alert" className="form-error">{error}</p>}
    {success && <p role="status">{success}</p>}
    <button className="action-button" type="submit" disabled={pending}>{pending ? "Please wait…" : submitLabel}</button>
  </form>;
}

export function AccountSettings({ profile }: { profile: AccountProfile }) {
  const [saved, setSaved] = useState(profile);
  const [name, setName] = useState(profile.display_name ?? "");
  const [photo, setPhoto] = useState<File | null>(null);
  const [removePhoto, setRemovePhoto] = useState(false);
  const [photoVersion, setPhotoVersion] = useState(0);

  return <div className={styles.grid}>
    <SettingsForm title="Profile" submitLabel="Save profile" onSave={async () => {
      const updated = await api<AccountProfile>("/account/profile", "PATCH", {
        display_name: name,
        ...(removePhoto ? { avatar_pixels: null } : photo ? { avatar_pixels: await picturePixels(photo) } : {}),
      });
      setSaved(updated);
      setName(updated.display_name ?? "");
      setPhoto(null);
      setRemovePhoto(false);
      setPhotoVersion(photoVersion + 1);
      return "Profile saved.";
    }}>
      <div className={styles.avatar}>
        {saved.avatar && !removePhoto
          ? <Image src={saved.avatar} width={56} height={56} unoptimized alt="Your profile picture" />
          : <span className="workspace-avatar" aria-hidden="true">{(saved.display_name || saved.email)[0].toUpperCase()}</span>}
        <div className="form-field">
          <label htmlFor="profile-picture">Profile picture</label>
          <input key={photoVersion} id="profile-picture" type="file" accept="image/png,image/jpeg"
            onChange={event => { setPhoto(event.target.files?.[0] ?? null); setRemovePhoto(false); }} />
        </div>
      </div>
      {saved.avatar && <div className={styles.actions}>
        <button className="subtle-button" type="button"
          onClick={() => { setRemovePhoto(!removePhoto); setPhoto(null); setPhotoVersion(photoVersion + 1); }}>
          {removePhoto ? "Keep current picture" : "Remove picture"}
        </button>
      </div>}
      <div className="form-field">
        <label htmlFor="display-name">Display name</label>
        <input id="display-name" name="display_name" autoComplete="name"
          maxLength={80} value={name} onChange={event => setName(event.target.value)} />
      </div>
    </SettingsForm>

    <section className={`auth-card auth-form ${styles.card}`}>
      <h2>Sign-in methods</h2>
      <ul>
        {profile.password_enabled && <li>Email and password</li>}
        {profile.google_linked && <li>Google</li>}
      </ul>
      {!profile.password_enabled && profile.google_linked && <p>You use Google to sign in to this account.</p>}
    </section>

    {(profile.password_enabled || profile.email_verified) ?
      <SettingsForm title="Email address" submitLabel="Request email change" onSave={async (data) => {
        await api("/account/email/request", "POST", {
          email: data.get("email"),
          ...(profile.password_enabled ? { current_password: data.get("email_password") } : {}),
        });
        return profile.password_enabled
          ? "Check your new inbox for verification. Open the link in this browser."
          : "Check your current inbox to approve the change in this browser.";
      }}>
        <p>Current email: {profile.email}</p>
        <div className="form-field">
          <label htmlFor="new-email">New email address</label>
          <input id="new-email" name="email" type="email" autoComplete="email" maxLength={320} required />
        </div>
        {profile.password_enabled && <PasswordField name="email_password" label="Current password for email change" />}
      </SettingsForm> :
      <section className={`auth-card auth-form ${styles.card}`}>
        <h2>Email address</h2>
        <p>{profile.email}</p>
        <Link href="/verification-required">Verify your current email before changing it</Link>
      </section>}

    {profile.password_enabled && <SettingsForm title="Password" submitLabel="Change password" onSave={async (data) => {
      if (data.get("password") !== data.get("password_confirmation")) throw new FormError("Passwords must match.");
      await api("/account/password", "POST", {
        current_password: data.get("current_password"),
        password: data.get("password"),
        password_confirmation: data.get("password_confirmation"),
      });
      window.location.replace("/login");
      return "Password updated. Sign in again.";
    }}>
      <PasswordField name="current_password" label="Current password" />
      <p className="field-help" id="password-help">Use 15–128 characters. Changing your password signs out all sessions.</p>
      <PasswordField name="password" label="New password" register />
      <PasswordField name="password_confirmation" label="Confirm new password" register />
    </SettingsForm>}
    <DangerZone password={profile.password_enabled} />
  </div>;
}
