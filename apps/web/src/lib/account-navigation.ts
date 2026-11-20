export const accountPathHeader = "x-resolveflow-account-path";
export const accountHome = "/app";

export function accountDestination(value: string | string[] | undefined | null): string {
  if (typeof value !== "string" || value.length > 2048 || /[\s#\\\p{Cc}]/u.test(value)) {
    return accountHome;
  }
  const path = value.split("?", 1)[0];
  // Current account routes use static slugs and UUIDs. Reject encoded and dot
  // path segments before a browser can normalize them.
  return /^\/app(?:\/[a-z0-9-]+)*\/?$/i.test(path) ? value : accountHome;
}

export function accountEntry(page: "/login" | "/register", destination?: string | null) {
  const next = accountDestination(destination);
  return next === accountHome ? page : `${page}?${new URLSearchParams({ next })}`;
}
