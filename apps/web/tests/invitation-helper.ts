import { expect, type APIRequestContext } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

export async function invitationCode(workspace: string, invitation: string): Promise<string> {
  if (process.env.RESOLVEFLOW_E2E_ISOLATED !== "1") throw new Error("Isolated test mailbox required");
  const root = process.env.RESOLVEFLOW_INVITATION_DELIVERY_ROOT;
  if (!root || !/^[a-f0-9-]{36}$/.test(workspace) || !/^[a-f0-9-]{36}$/.test(invitation)) throw new Error("Invalid test mailbox identity");
  return JSON.parse(await readFile(join(root, workspace.replaceAll("-", ""), invitation.replaceAll("-", "")), "utf8")).token;
}

async function post(client: APIRequestContext, path: string, data: unknown) {
  const csrf = await client.get("http://127.0.0.1:3100/api/v1/auth/csrf");
  expect(csrf.status()).toBe(200);
  return client.post("http://127.0.0.1:3100/api/v1" + path, { data, headers: {
    Origin: "http://127.0.0.1:3100", "X-CSRF-Token": (await csrf.json()).csrf_token,
  } });
}

export async function inviteMember(owner: APIRequestContext, target: APIRequestContext, membersPath: string, data: unknown) {
  const response = await post(owner, membersPath.replace(/\/members$/, "/invitations"), data);
  expect(response.status()).toBe(202);
  const invitation = await response.json();
  expect(invitation.token).toBeUndefined();
  const token = await invitationCode(membersPath.split("/")[2], invitation.id);
  return post(target, "/auth/invitations/accept", { token });
}
