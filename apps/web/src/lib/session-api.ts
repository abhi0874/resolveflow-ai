export class ApiError extends Error {
  constructor(public status: number, public code?: string) {
    super(`Request failed (${status})`);
  }
}

export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (method !== "GET") {
    const csrf = await fetch("/api/v1/auth/csrf", {
      credentials: "same-origin",
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    });
    if (!csrf.ok) throw new ApiError(csrf.status);
    headers["X-CSRF-Token"] = (await csrf.json()).csrf_token;
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers,
    credentials: "same-origin",
    cache: "no-store",
    body: method === "GET" ? undefined : JSON.stringify(body ?? {}),
    signal: AbortSignal.timeout(path.includes("/workflows") ? 120000 : /\/(index|generate-response)$/.test(path) ? 60000 : 15000),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new ApiError(response.status, typeof error?.error?.code === "string" ? error.error.code : undefined);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function errorMessage(error: unknown, auth = false): string {
  if (error instanceof ApiError) {
    if (error.code === "email_verification_required")
      return "Verify your email before signing in. Use the Verify email link below to request another message.";
    if (error.status === 401) {
      if (!auth) window.location.replace("/login?expired=1");
      return auth
        ? "Email or password is incorrect."
        : "Your session has expired. Please sign in again.";
    }
    if (error.status === 403)
      return "This action is not permitted, or the form has expired. Refresh and try again.";
    if (error.status === 409)
      return auth
        ? "Unable to create this account. Try signing in or use another email."
        : "This change conflicts with an existing record or would remove the last owner.";
    if (error.status === 422)
      return auth
        ? "Check your email and use matching passwords of 15–128 characters."
        : "Check your entries. Members must already have a registered account.";
    if (error.status === 429)
      return "Too many attempts. Please wait 15 minutes before trying again.";
  }
  return "We couldn’t reach the service. Check your connection and try again.";
}

export type User = { id: string; email: string; email_verified: boolean };
export type Role = "owner" | "admin" | "support_agent" | "viewer";
export type Workspace = {
  id: string;
  name: string;
  slug: string;
  role: Role;
  permissions: string[];
};
export type Member = { user_id: string; email: string; role: Role };
