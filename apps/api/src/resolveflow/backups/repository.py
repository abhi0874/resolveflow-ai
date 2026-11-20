"""Scoped restic repository. Secrets use a private file, never argv or status."""

import json
import os
import re
import secrets
import shutil
import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from resolveflow.backups.safety import private, require, run, safe_path, save_json


class BackupConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository: Path
    password_file: Path
    restic_binary: Path
    pg_bin: Path
    repository_id: str
    keep_daily: int = Field(default=7, ge=1, le=365)
    keep_weekly: int = Field(default=4, ge=1, le=104)
    keep_monthly: int = Field(default=3, ge=1, le=120)
    max_age_hours: int = Field(default=26, ge=1, le=8760)
    min_free_bytes: int = Field(default=256 * 1024**2, ge=1024**2)


class Repository:
    def __init__(self, state: Path):
        private(state, directory=True)
        private(state / "config.json")
        self.state = state
        self.config = BackupConfig.model_validate_json((state / "config.json").read_text())
        c = self.config
        private(c.password_file)
        private(c.repository, directory=True)
        for path in (c.restic_binary, c.pg_bin):
            safe_path(path)
        require(not c.password_file.is_relative_to(c.repository), "key_inside_repository")
        require(c.password_file.stat().st_size >= 32, "missing_encryption_credential")
        require(
            json.loads(self.call("cat", "config"))["id"] == c.repository_id,
            "repository_identity_mismatch",
        )

    def call(self, *args, cwd=None):
        c = self.config
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.state),
            "RESTIC_REPOSITORY": str(c.repository),
            "RESTIC_PASSWORD_FILE": str(c.password_file),
        }
        return run(c.restic_binary, ["--no-cache", *args], env, cwd=cwd)

    def snapshots(self):
        return json.loads(self.call("snapshots", "--json", "--tag", "resolveflow-v1"))

    def select(self, identity):
        require(identity == "latest" or re.fullmatch(r"[a-f0-9]{64}", identity), "invalid_snapshot")
        snapshots = self.snapshots()
        require(snapshots, "no_snapshots")
        if identity == "latest":
            return max(snapshots, key=lambda s: s["time"])["id"]
        require(any(s["id"] == identity for s in snapshots), "snapshot_not_in_scope")
        return identity

    def check(self):
        self.call("check", "--read-data")
        self.event("integrity", {"ok": True})

    def event(self, name, data):
        path = self.state / "status.json"
        if path.exists():
            private(path)
        previous = json.loads(path.read_text()) if path.exists() else {}
        previous[name] = {"at": time.time(), **data}
        save_json(path, previous)

    def status(self):
        path = self.state / "status.json"
        if path.exists():
            private(path)
        data = json.loads(path.read_text()) if path.exists() else {}
        age = time.time() - data.get("backup", {}).get("at", 0)
        return {
            **data,
            "backup_age_seconds": round(age),
            "stale": age > self.config.max_age_hours * 3600,
            "repository_available": True,
            "incomplete_stages": len(list(self.state.glob("snapshot-*")))
            + len(list(self.state.glob("restore-test-*"))),
            "repository_bytes": sum(
                p.stat().st_size
                for p in self.config.repository.rglob("*")
                if p.is_file() and not p.is_symlink()
            ),
            "destination_free_bytes": shutil.disk_usage(self.config.repository).free,
        }

    def retention(self, apply=False):
        self.check()
        latest = self.select("latest")
        status = self.status()
        require(status.get("restore", {}).get("snapshot") == latest, "latest_restore_required")
        c = self.config
        args = [
            "forget",
            "--tag",
            "resolveflow-v1",
            "--group-by",
            "tags",
            "--keep-last",
            "2",
            "--keep-daily",
            str(c.keep_daily),
            "--keep-weekly",
            str(c.keep_weekly),
            "--keep-monthly",
            str(c.keep_monthly),
        ]
        if not apply:
            args.append("--dry-run")
        else:
            args.append("--prune")
        self.call(*args)
        remaining = self.snapshots()
        require(any(s["id"] == latest for s in remaining), "retention_verification_failed")
        return {
            "applied": apply,
            "remaining": len(remaining),
            "latest_preserved": True,
            "daily": c.keep_daily,
            "weekly": c.keep_weekly,
            "monthly": c.keep_monthly,
        }


def initialize(state: Path, repository: Path, restic: Path, pg_bin: Path):
    for path in (state, repository, restic, pg_bin):
        safe_path(path)
    require(not state.exists() and not repository.exists(), "destination_exists")
    require(
        not state.is_relative_to(repository) and not repository.is_relative_to(state),
        "overlapping_destinations",
    )
    state.mkdir(mode=0o700, parents=True)
    repository.mkdir(mode=0o700, parents=True)
    key = state / "repository-password"
    with open(key, "x", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
        stream.write(secrets.token_urlsafe(48) + "\n")
    config = BackupConfig(
        repository=repository,
        password_file=key,
        restic_binary=restic,
        pg_bin=pg_bin,
        repository_id="pending",
    )
    # Initialization uses only these explicit local paths; no inherited backend credentials.
    provisional = object.__new__(Repository)
    provisional.state, provisional.config = state, config
    provisional.call("init", "--repository-version", "2")
    config.repository_id = json.loads(provisional.call("cat", "config"))["id"]
    save_json(state / "config.json", config.model_dump(mode="json"))
    return Repository(state)
