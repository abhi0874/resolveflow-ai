export const sessionCookieNames = ["resolveflow_session", "__Host-resolveflow_session"];

export function isSessionToken(value: string | undefined): value is string {
  return value !== undefined && /^[A-Za-z0-9_-]{43}$/.test(value);
}
