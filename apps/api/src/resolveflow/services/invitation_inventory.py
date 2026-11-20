"""Read-only operator inventory. A classification never authorizes file removal."""

import json
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import select

from resolveflow.db.models import InvitationDelivery, WorkspaceInvitation
from resolveflow.services.auth import digest
from resolveflow.services.invitation_files import UnverifiedFile, checksum, read_private

ID = r"[0-9a-f]{32}"
OBJECT = re.compile(rf"({ID})(?:\.([0-9a-f]{{64}}))?(\.part)?")


@contextmanager
def private_directory(name, parent=None):
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise UnverifiedFile
        yield fd
    finally:
        os.close(fd)


def classify(db, folder, workspace_id, name, root_hash):
    match = OBJECT.fullmatch(name)
    if not match:
        return "hold_unknown_name"
    identifier, attempt, partial = match.groups()
    record_id = uuid.UUID(identifier)
    intent = db.get(InvitationDelivery, record_id)
    data = read_private(folder, name)
    if data is None:
        return "hold_changed_during_inventory"
    content_hash = checksum(data)
    if intent:
        if intent.workspace_id != workspace_id or intent.mailbox_hash != root_hash:
            return "hold_location_mismatch"
        if partial and attempt in intent.attempts:
            return (
                "verified_stage" if content_hash == attempt else "hold_incomplete_or_altered_stage"
            )
        if not partial and not attempt and content_hash == intent.attempts[-1]:
            return "verified_final"
        return "hold_unverified_content"
    # Legacy filenames or addresses alone are insufficient. Match the secret
    # commitment too, without including the secret or personal fields in output.
    invitation = db.get(WorkspaceInvitation, record_id)
    if not invitation or invitation.workspace_id != workspace_id or attempt or partial:
        return "hold_missing_ownership"
    try:
        value = json.loads(data)
        if (
            isinstance(value, dict)
            and value.get("kind") == "local_synthetic_invitation"
            and set(value) == {"kind", "recipient", "workspace", "token", "expires_at"}
            and isinstance(value.get("token"), str)
            and value.get("recipient") == invitation.email
            and digest(value["token"]) == invitation.token_hash
        ):
            return "legacy_correlated"
    except ValueError, UnicodeError, RecursionError:
        pass
    return "hold_unverified_legacy"


def existing_files(db, root: Path, root_hash):
    if not os.path.lexists(root):
        return
    with private_directory(root) as root_fd:
        for name in sorted(os.listdir(root_fd)):
            if not re.fullmatch(ID, name):
                yield digest(name), "hold_unknown_directory"
                continue
            try:
                with private_directory(name, root_fd) as folder:
                    for leaf in sorted(os.listdir(folder)):
                        ref = digest(name + "/" + leaf)
                        try:
                            status = classify(db, folder, uuid.UUID(name), leaf, root_hash)
                        except UnverifiedFile, OSError:
                            status = "hold_unsafe_or_unreadable"
                        yield ref, status
            except UnverifiedFile, OSError:
                yield digest(name), "hold_unsafe_directory"


def inventory(db, root: Path):
    root_hash = digest(str(root.resolve()))
    observed = set()
    for ref, classification in existing_files(db, root, root_hash):
        observed.add(ref)
        yield ref, classification
    delivered = select(InvitationDelivery.workspace_id, InvitationDelivery.id).where(
        InvitationDelivery.mailbox_hash == root_hash, InvitationDelivery.status == "delivered"
    )
    for workspace_id, invitation_id in db.execute(delivered):
        ref = digest(workspace_id.hex + "/" + invitation_id.hex)
        if ref not in observed:
            yield ref, "hold_missing_or_inaccessible_final"
