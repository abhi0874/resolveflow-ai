"""Private local objects. Keys are generated IDs; never user filenames."""

import os
import re
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def save(self, workspace_id: uuid.UUID, key: str, content: bytes) -> None: ...
    def read(self, workspace_id: uuid.UUID, key: str, limit: int) -> bytes: ...
    def delete(self, workspace_id: uuid.UUID, key: str) -> None: ...
    def exists(self, workspace_id: uuid.UUID, key: str) -> bool: ...


class LocalFileStorage:
    def __init__(self, root: Path):
        self.root = root

    @contextmanager
    def directory(self, workspace_id: uuid.UUID, key: str):
        if not isinstance(workspace_id, uuid.UUID) or not re.fullmatch(r"[a-f0-9]{32}", key):
            raise ValueError("Invalid storage identity")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            if os.fstat(root_fd).st_mode & 0o077:
                raise OSError("Storage directory must be private")
            name = workspace_id.hex
            try:
                os.mkdir(name, mode=0o700, dir_fd=root_fd)
            except FileExistsError:
                pass
            folder_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
            try:
                if os.fstat(folder_fd).st_mode & 0o077:
                    raise OSError("Workspace storage must be private")
                yield folder_fd
            finally:
                os.close(folder_fd)
        finally:
            os.close(root_fd)

    def save(self, workspace_id: uuid.UUID, key: str, content: bytes) -> None:
        with self.directory(workspace_id, key) as folder:
            # A deterministic partial object stays associated with its DB journal on a crash.
            fd = os.open(
                key + ".part",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=folder,
            )
            with os.fdopen(fd, "wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(key + ".part", key, src_dir_fd=folder, dst_dir_fd=folder)
            os.fsync(folder)

    def read(self, workspace_id: uuid.UUID, key: str, limit: int) -> bytes:
        with self.directory(workspace_id, key) as folder:
            fd = os.open(key, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
            with os.fdopen(fd, "rb") as source:
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                    raise OSError("Not a regular object")
                data = source.read(limit + 1)
                if len(data) > limit:
                    raise OSError("Object exceeds limit")
                return data

    def delete(self, workspace_id: uuid.UUID, key: str) -> None:
        with self.directory(workspace_id, key) as folder:
            for name in (key, key + ".part"):
                try:
                    os.unlink(name, dir_fd=folder)
                except FileNotFoundError:
                    pass
            os.fsync(folder)

    def exists(self, workspace_id: uuid.UUID, key: str) -> bool:
        with self.directory(workspace_id, key) as folder:
            try:
                return stat.S_ISREG(os.stat(key, dir_fd=folder, follow_symlinks=False).st_mode)
            except FileNotFoundError:
                return False
