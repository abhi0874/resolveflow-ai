import "server-only";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { accountEntry, accountPathHeader } from "./account-navigation";
import { serverGet } from "./server-api";
import type { User, Workspace } from "./session-api";

export async function readPrivate(path: string): Promise<Response | null> {
  const response = await serverGet(path).catch(() => null);
  if (response?.status === 401) {
    redirect(accountEntry("/login", (await headers()).get(accountPathHeader)));
  }
  if (response?.status === 403) {
    const failure = await response.json().catch(() => null);
    if (failure?.error?.code === "email_verification_required") {
      redirect("/verification-required");
    }
  }
  return response?.ok ? response : null;
}

export async function workspaceAccess() {
  // Validate with FastAPI before fetching or rendering any workspace data.
  const identity = await readPrivate("/auth/me");
  if (!identity) return null;
  const spaces = await readPrivate("/workspaces");
  if (!spaces) return null;
  const user: User = await identity.json();
  const workspaces: Workspace[] = await spaces.json();
  return { user, workspaces };
}
