"""All workspace access flows through this membership/permission boundary."""

import uuid
from enum import StrEnum

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from resolveflow.db.models import MembershipRole, User, Workspace, WorkspaceMembership
from resolveflow.schemas.auth import WorkspaceResponse


class Permission(StrEnum):
    ANALYTICS = "analytics:read"
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_CONTENT = "document:content"
    DOCUMENT_DELETE = "document:delete"
    TICKET_WRITE = "ticket:write"
    TICKET_MANAGE = "ticket:manage"
    READ = "workspace:read"
    SETTINGS = "workspace:settings"
    MEMBERS = "workspace:members"


PERMISSIONS = {
    MembershipRole.OWNER: frozenset(Permission),
    MembershipRole.ADMIN: frozenset(Permission),
    MembershipRole.SUPPORT_AGENT: frozenset(
        {
            Permission.READ,
            Permission.TICKET_WRITE,
            Permission.DOCUMENT_UPLOAD,
            Permission.DOCUMENT_CONTENT,
        }
    ),
    MembershipRole.VIEWER: frozenset({Permission.READ}),
}


def access(
    db: Session,
    user: User,
    workspace_id: uuid.UUID,
    permission: Permission = Permission.READ,
    *,
    lock: bool = False,
):
    # Serialize every membership/settings mutation on one workspace row. Query
    # membership after obtaining the lock so a concurrent demotion cannot be stale.
    query = select(Workspace).where(Workspace.id == workspace_id)
    workspace = db.scalar(query.with_for_update() if lock else query)
    membership = db.scalar(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id, WorkspaceMembership.user_id == user.id
        )
        .execution_options(populate_existing=True)
    )
    if workspace is None or membership is None:
        raise HTTPException(404)  # Same answer for nonexistent and unauthorized tenants.
    if permission not in PERMISSIONS[membership.role]:
        raise HTTPException(403)
    return workspace, membership


def workspace_response(workspace: Workspace, membership: WorkspaceMembership) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        role=membership.role,
        permissions=sorted(PERMISSIONS[membership.role]),
    )


def check_member_change(
    db: Session,
    actor: WorkspaceMembership,
    target: WorkspaceMembership | None,
    new_role: MembershipRole | None,
):
    # Admins can add/edit/remove agents and viewers only, including no changes to
    # their own admin membership. Only owners can manage admins or ownership.
    if actor.role != MembershipRole.OWNER:
        allowed = {MembershipRole.SUPPORT_AGENT, MembershipRole.VIEWER}
        if (target is not None and target.role not in allowed) or (
            new_role is not None and new_role not in allowed
        ):
            raise HTTPException(403)
    if target and target.role == MembershipRole.OWNER and new_role != MembershipRole.OWNER:
        owners = db.scalar(
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == actor.workspace_id,
                WorkspaceMembership.role == MembershipRole.OWNER,
            )
        )
        if owners <= 1:
            raise HTTPException(409)
