"""Private paths, bounded subprocesses and non-content diagnostics."""

import fcntl
import hashlib
import json
import os
import stat
import subprocess
from contextlib import contextmanager
from pathlib import Path


class BackupError(Exception):
    """Only fixed, non-sensitive category strings cross the CLI boundary."""


def require(value, code):
    if not value:
        raise BackupError(code)


def safe_path(path: Path):
    require(path.is_absolute() and ".." not in path.parts, "unsafe_path")
    for parent in [path, *path.parents]:
        require(not parent.is_symlink(), "symlink_rejected")
    return path


def private(path: Path, *, directory=False):
    safe_path(path)
    info = path.stat()
    require(info.st_uid == os.getuid() and not info.st_mode & 0o077, "private_permissions_required")
    require(
        stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), "unsafe_file_type"
    )


def save_json(path, value):
    safe_path(path)
    temp = path.with_suffix(".new")
    with open(temp, "x", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def sha256(path):
    safe_path(path)
    require(path.is_file(), "missing_file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(binary, args, env, *, cwd=None, timeout=600):
    try:
        result = subprocess.run(
            [str(binary), *map(str, args)],
            env=env,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except OSError, subprocess.TimeoutExpired:
        raise BackupError("tool_unavailable_or_timeout") from None
    require(result.returncode == 0, "tool_failed")
    return result.stdout


@contextmanager
def exclusive(directory):
    private(directory, directory=True)
    fd = os.open(directory / "operation.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BackupError("backup_operation_busy") from None
        yield
    finally:
        os.close(fd)
