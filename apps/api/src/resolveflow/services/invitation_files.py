"""Create-only local invitation publication under a committed content digest."""

import hashlib
import os
import stat


class UnverifiedFile(Exception):
    pass


def read_private(folder, name, *, sync=False):
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise UnverifiedFile
    with os.fdopen(fd, "rb") as f:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or info.st_size > 8192
        ):
            raise UnverifiedFile
        data = f.read(8193)
        if len(data) > 8192:
            raise UnverifiedFile
        if sync:
            os.fsync(fd)
        return data


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def publish_new(folder, key, data):
    """The caller holds the row lock. Never replace a final file or truncate a partial."""
    stage = f"{key}.{checksum(data)}.part"
    existing = read_private(folder, key, sync=True)
    if existing is not None and existing != data:
        raise UnverifiedFile
    partial = read_private(folder, stage, sync=True)
    if partial is not None and partial != data:
        raise UnverifiedFile
    if existing is None:
        if partial is None:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            with os.fdopen(os.open(stage, flags, 0o600, dir_fd=folder), "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        os.link(stage, key, src_dir_fd=folder, dst_dir_fd=folder, follow_symlinks=False)
        os.fsync(folder)
    if partial is not None or existing is None:
        os.unlink(stage, dir_fd=folder)
    os.fsync(folder)
