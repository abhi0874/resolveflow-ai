# Workspace and ticket authorization — Steps 4–5

**Step 19B:** production requires exact-address SMTP verification before login or
privileged workspace access; the backend enforces this even for pre-existing
sessions and queued workflow actors. Local development can retain its compatibility
policy; no client flag controls it. Recovery changes credentials and invalidates
sessions/tokens without adding membership or changing roles. Prior local proof is
not promoted to production identity. Workspace invitation transport remains the
separate local-only implementation; see [EMAIL_DELIVERY.md](EMAIL_DELIVERY.md).

**Local follow-up, 2026-10-23:** new membership grants require account-bound,
expiring invitation acceptance. The legacy POST members route now returns 409
after authorization instead of granting access. Existing role-change/removal
protections remain. The route table and original invitation limitations below
describe the historical Steps 4–5 implementation; current routes and synthetic
delivery restrictions are in [IDENTITY_AND_RECOVERY.md](IDENTITY_AND_RECOVERY.md).

Implemented and verified 2026-10-19. Authentication identifies the caller;
workspace membership and permissions determine what they may do. Neither a
frontend selector nor possession of a workspace UUID grants access.

## Central policy

`services/authorization.py` defines permissions and the `access` boundary.
Every workspace-specific route authenticates the current session, loads the target
workspace and the current user's membership, and enforces the required permission.
Nonmembers and nonexistent workspaces both receive 404. Members without the
required permission receive 403. Membership role changes take effect on the next
request; roles are not cached in cookies or trusted from client input.

| Operation | Owner | Admin | Support agent | Viewer |
| --- | --- | --- | --- | --- |
| Read own workspace and its member list | Yes | Yes | Yes | Yes |
| Update workspace name/slug | Yes | Yes | No | No |
| Add/change/remove agents and viewers | Yes | Yes | No | No |
| Add/change/remove admins | Yes | No | No | No |
| Grant Owner role / modify owners | Yes, preserving one owner | No | No | No |
| Access another workspace without membership | No | No | No | No |

Any authenticated active user may create a new workspace. Creation inserts the
workspace and Owner membership in one transaction; conflict/failure rolls back
both. List queries join through the current user's memberships. Slugs remain
globally unique and validated against the original database rule.

Members can read teammates' email addresses within their authorized workspace.
Only owners/admins may add an existing **active** registered user; there are no
invitation emails or public user-directory endpoints. An Admin cannot alter
another admin, any owner, or their own admin membership, and cannot grant either
privileged role. Owners can grant additional ownership; the final owner cannot
be removed or demoted. An owner can remove themselves only when another owner
remains. Workspace deletion is not implemented.

## Transaction and tenant boundaries

Settings and membership mutations first take `SELECT ... FOR UPDATE` on the
workspace row, then re-read the acting membership. Every membership mutation uses
this lock, serializing owner-count checks and preventing stale permissions after
concurrent demotion. Last-owner changes count owners within that transaction.
A concurrent two-owner self-removal test verifies exactly one succeeds and one
receives 409, leaving one owner. This invariant applies to application routes;
a database administrator can bypass application policy with raw SQL.

The target member query includes **both** workspace ID and user ID. Supplying a
user or membership identifier from a different tenant cannot redirect the write.
Unique `(workspace_id,user_id)` constraints and FK restrictions remain in force.
Role values are validated enums. Client forms receive permission names for UI
presentation, but backend checks run independently for direct requests.

Active-workspace selection is a non-secret URL parameter on `/app?workspace=UUID`.
The server resolves it only against the user's authorized workspace list and
fetches members through the protected backend. Invalid/unauthorized selections
render no workspace records. Selection does not modify authentication state or
become trusted authorization context. No session credential is stored in
localStorage or a URL.

## Endpoints

Paths below are relative to `/api/v1`. Mutations require JSON, Origin and CSRF as
described in [AUTHENTICATION.md](AUTHENTICATION.md).

| Method/path | Permission and response |
| --- | --- |
| POST `/workspaces` | Authenticated user; name/slug; 201 workspace + Owner role |
| GET `/workspaces` | Authenticated user; only their memberships/workspaces |
| GET `/workspaces/{workspace_id}` | Member; safe workspace details/role/permissions |
| PATCH `/workspaces/{workspace_id}` | Owner/Admin; name and slug; 200 updated workspace |
| GET `/workspaces/{workspace_id}/members` | Member; authorized tenant's user IDs/emails/roles |
| POST `/workspaces/{workspace_id}/members` | Owner/Admin within role boundaries; existing email + role; 201 |
| PATCH `/workspaces/{workspace_id}/members/{user_id}` | Owner/Admin within boundaries; role; 200 |
| DELETE `/workspaces/{workspace_id}/members/{user_id}` | Owner/Admin within boundaries; 204 |

PATCH workspace currently requires both name and slug. Duplicate slug/membership
returns safe 409; a missing/inactive account for addition returns generic 422.
The UI displays actionable errors, pending states and access-appropriate controls.
No role permits unauthenticated operations.

## Resource authorization

Step 5 ticket and Step 6 document routes implement the following pattern. Future
retrieval and AI workflow routes must also:

1. Authenticate using the backend dependency.
2. Call the central workspace access function for its required permission.
3. Query the requested resource using **both its ID and the authorized workspace ID**.
4. Return 404 if that scoped query finds nothing; never fetch globally and trust a
   client claim that it belongs to the selected workspace.
5. Keep privileged mutations transactional, and test direct requests across tenants.

Step 5 adds ticket:write for Owner/Admin/Support Agent and ticket:manage for
Owner/Admin. Support agents edit only unassigned or self-assigned tickets, create
medium/unassigned tickets and may add notes to any workspace ticket. Only
Owner/Admin change assignment/priority. Viewer reads only, including internal
notes. All writes lock the workspace and re-read membership; stale ticket versions
produce 409. Membership removal or Viewer demotion atomically unassigns tickets
with an activity event. See [TICKET_MANAGEMENT.md](TICKET_MANAGEMENT.md) for the
complete matrix, eligible assignees and endpoint contracts. Workers/retrieval/checkpoints must enforce
identical tenant boundaries when introduced. No database row-level security is
implemented, so application checks are mandatory, including future non-HTTP paths.

## Verified and deferred

Backend integration tests exercise workspace/owner creation, listing, authorized
reads and edits, foreign-tenant reads/writes/member operations, duplicate membership,
Viewer and Support Agent write rejection, Admin escalation/owner interference,
permitted lower-role management, revocation on the next request, final-owner
removal/demotion and concurrent owner removal. Browser tests verify real membership
addition/role change/removal, workspace switching and Viewer control visibility.
The additive authentication migration was upgraded, downgraded to 0002 and reapplied
on a disposable database while preserving an existing workspace record.

Step 5 adds ticket APIs and application-level append-only ticket activity.
Invitations, verified-email requirements, workspace deletion, background jobs and
RLS remain deferred. Production should review
member-list privacy, membership auditing, transaction/load behavior, runtime database
least privilege and owner recovery before public use. Steps 4–5 are complete; later
product workflows require a separate user instruction.

## Step 6 document permissions

All members may list/read document metadata and upload configuration. Owner/Admin
and Support Agent have document:upload (including retry) and document:content
(chunks/download); only Owner/Admin have document:delete. Viewers cannot access
raw or extracted content. Resource reads and writes are scoped by workspace and
document together. Privileged writes recheck membership under the workspace lock;
bounded processing then holds only a document lock. The operator recovery command
is trusted maintenance across tenants, using each stored workspace/document pair;
it is not an unscoped user endpoint. See [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md).

## Step 7 classification permissions

Classification requires ticket:write plus the same assignment-aware require_editor
check used by ticket edits. Owner/Admin can classify all workspace tickets; Support
Agent only unassigned/self-assigned tickets; Viewer cannot classify. Tenant-scoped
reads, CSRF and exact Origin checks apply even though inference is nonmutating.
Acceptance reuses PATCH, rechecks authorization and expected_version, and preserves
activity. See [ML_CLASSIFICATION.md](ML_CLASSIFICATION.md).
