import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from resolveflow.db.models import (
    AccountStatus,
    MembershipRole,
    User,
    Workspace,
    WorkspaceMembership,
)
from resolveflow.schemas.auth import (
    MemberInput,
    MemberResponse,
    RoleInput,
    WorkspaceInput,
    WorkspaceResponse,
)
from resolveflow.services.auth import CSRF, DB, CurrentUser
from resolveflow.services.authorization import (
    Permission,
    access,
    check_member_change,
    workspace_response,
)
from resolveflow.services.tickets import unassign_member

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(db: DB, user: CurrentUser):
    rows = db.execute(
        select(Workspace, WorkspaceMembership)
        .join(WorkspaceMembership)
        .where(WorkspaceMembership.user_id == user.id)
        .order_by(Workspace.created_at, Workspace.id)
    ).all()
    return [workspace_response(workspace, membership) for workspace, membership in rows]


@router.post("", response_model=WorkspaceResponse, status_code=201)
def create_workspace(body: WorkspaceInput, db: DB, user: CurrentUser, csrf: CSRF):
    workspace = Workspace(name=body.name, slug=body.slug)
    db.add(workspace)
    db.flush()
    membership = WorkspaceMembership(
        workspace_id=workspace.id, user_id=user.id, role=MembershipRole.OWNER
    )
    db.add(membership)
    db.commit()
    return workspace_response(workspace, membership)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def workspace_details(workspace_id: uuid.UUID, db: DB, user: CurrentUser):
    return workspace_response(*access(db, user, workspace_id))


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: uuid.UUID, body: WorkspaceInput, db: DB, user: CurrentUser, csrf: CSRF
):
    workspace, membership = access(db, user, workspace_id, Permission.SETTINGS, lock=True)
    workspace.name, workspace.slug = body.name, body.slug
    db.commit()
    return workspace_response(workspace, membership)


@router.get("/{workspace_id}/members", response_model=list[MemberResponse])
def members(workspace_id: uuid.UUID, db: DB, user: CurrentUser):
    access(db, user, workspace_id)
    return [
        MemberResponse(user_id=member.user_id, email=email, role=member.role)
        for member, email in db.execute(
            select(WorkspaceMembership, User.email)
            .join(User)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(User.email)
        ).all()
    ]


@router.post("/{workspace_id}/members", response_model=MemberResponse, status_code=201)
def add_member(workspace_id: uuid.UUID, body: MemberInput, db: DB, user: CurrentUser, csrf: CSRF):
    _, actor = access(db, user, workspace_id, Permission.MEMBERS, lock=True)
    check_member_change(db, actor, None, body.role)
    target_user = db.scalar(
        select(User).where(
            User.email == str(body.email), User.account_status == AccountStatus.ACTIVE
        )
    )
    if target_user is None:
        raise HTTPException(422)  # No public account lookup endpoint.
    target = WorkspaceMembership(user_id=target_user.id, workspace_id=workspace_id, role=body.role)
    db.add(target)
    db.commit()
    return MemberResponse(user_id=target.user_id, email=target_user.email, role=target.role)


def target_member(db, workspace_id, user_id):
    target = db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id, WorkspaceMembership.user_id == user_id
        )
    )
    if target is None:
        raise HTTPException(404)
    return target


@router.patch("/{workspace_id}/members/{user_id}", response_model=MemberResponse)
def change_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    body: RoleInput,
    db: DB,
    user: CurrentUser,
    csrf: CSRF,
):
    _, actor = access(db, user, workspace_id, Permission.MEMBERS, lock=True)
    target = target_member(db, workspace_id, user_id)
    check_member_change(db, actor, target, body.role)
    if body.role == MembershipRole.VIEWER:
        unassign_member(db, workspace_id, user_id, user.id)
    target.role = body.role
    db.commit()
    return MemberResponse(user_id=user_id, email=db.get(User, user_id).email, role=target.role)


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
def remove_member(
    workspace_id: uuid.UUID, user_id: uuid.UUID, db: DB, user: CurrentUser, csrf: CSRF
):
    _, actor = access(db, user, workspace_id, Permission.MEMBERS, lock=True)
    target = target_member(db, workspace_id, user_id)
    check_member_change(db, actor, target, None)
    unassign_member(db, workspace_id, user_id, user.id)
    db.delete(target)
    db.commit()
