import { appMode } from "@/lib/app-mode";
import { NextRequest } from "next/server";
import { backendOrigin, sessionCookies } from "@/lib/server-api";

export const dynamic = "force-dynamic";
const allowedPath =
  /^(auth\/(csrf|register|login|logout|me)|workspaces(\/[a-f0-9-]{36}(\/members(\/[a-f0-9-]{36})?|\/tickets(\/assignees|\/[a-f0-9-]{36}(\/(notes|activities|classify))?)?|\/documents(\/config|\/[a-f0-9-]{36}(\/(chunks|download|retry|index))?)?)?)?)$/;
const draftPath = /^workspaces\/[a-f0-9-]{36}\/tickets\/[a-f0-9-]{36}\/(?:generate-response|response-config|drafts(?:\/[a-f0-9-]{36}(?:\/review)?)?)$/;

const analyticsPath = /^workspaces\/[a-f0-9-]{36}\/analytics\/overview$/;
const workflowPath = /^workspaces\/[a-f0-9-]{36}\/(?:tickets\/[a-f0-9-]{36}\/workflows|workflows\/[a-f0-9-]{36}(?:\/(?:resume|cancel))?)$/;

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  if (appMode() === "demo") return new Response(null, { status: 404 });
  const path = (await context.params).path.join("/");
  const upload =
    request.method === "POST" &&
    /^workspaces\/[a-f0-9-]{36}\/documents$/.test(path);
  const documentRequest = path.includes("/documents");
  const query = request.nextUrl.searchParams;
  const keys = new Set([
    "search",
    "status",
    "priority",
    "category",
    "assignee",
    "sort",
    "direction",
    "page",
    "page_size",
  ]);
  const analyticsQuery = request.method === "GET" && analyticsPath.test(path) && request.nextUrl.search.length <= 128 && [...query.keys()].every(key => ["start", "end"].includes(key) && query.getAll(key).length === 1);
  const queryAllowed =
    request.method === "GET" &&
    /\/(?:tickets(?:\/[a-f0-9-]{36}\/(?:notes|activities|drafts|workflows))?|documents(?:\/[a-f0-9-]{36}\/chunks)?)$/.test(
      path,
    ) &&
    [...query.keys()].every(
      (key) => keys.has(key) && query.getAll(key).length === 1,
    ) &&
    request.nextUrl.search.length <= 2048;
  if ((!analyticsPath.test(path) && !allowedPath.test(path) && !draftPath.test(path) && !workflowPath.test(path) && !/^workspaces\/[a-f0-9-]{36}\/knowledge-base\/search$/.test(path)) || (request.nextUrl.search && !queryAllowed && !analyticsQuery))
    return new Response(null, { status: 404 });
  const headers = new Headers({ cookie: await sessionCookies() });
  for (const name of [
    "origin",
    "content-type",
    "x-csrf-token",
    "sec-fetch-site",
    ...(upload ? ["x-upload-filename"] : []),
  ]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  let body: Uint8Array | undefined;
  if (request.body && request.method !== "GET") {
    const reader = request.body.getReader();
    const chunks: Uint8Array[] = [];
    let length = 0;
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      length += chunk.value.byteLength;
      if (length > (upload ? 5 * 1024 * 1024 : 16384)) {
        await reader.cancel();
        return Response.json(
          { error: { message: "Request is too large" } },
          { status: 413 },
        );
      }
      chunks.push(chunk.value);
    }
    body = new Uint8Array(length);
    let offset = 0;
    for (const chunk of chunks) {
      body.set(chunk, offset);
      offset += chunk.length;
    }
  }
  try {
    const upstream = await fetch(
      `${backendOrigin()}/api/v1/${path}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body: body as BodyInit | undefined,
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(documentRequest || path.endsWith("/generate-response") ? 60000 : 15000),
      },
    );
    const outgoing = new Headers({
      "cache-control": "no-store",
      vary: "Cookie",
      "x-content-type-options": "nosniff",
    });
    for (const name of [
      "x-request-id",
      "content-type",
      "retry-after",
      "content-disposition",
      "content-security-policy",
    ]) {
      const value = upstream.headers.get(name);
      if (value) outgoing.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie())
      outgoing.append("set-cookie", cookie);
    return new Response(upstream.body, {
      status: upstream.status,
      headers: outgoing,
    });
  } catch {
    return Response.json(
      { error: { message: "Service is temporarily unavailable" } },
      { status: 503, headers: { "cache-control": "no-store" } },
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as DELETE };
