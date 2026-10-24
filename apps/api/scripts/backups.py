"""Offline local encrypted backup operations. See docs/BACKUP_OPERATIONS.md."""

import argparse
import json
import os
import plistlib
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from resolveflow.backups.repository import Repository, initialize
from resolveflow.backups.safety import (
    BackupError,
    exclusive,
    private,
    require,
    safe_path,
    save_json,
)
from resolveflow.backups.service import capture, restore_into
from resolveflow.core.config import Settings
from scripts.local_db import BIN, DATA, admin_connect, load_state, url

ROOT = Path(__file__).resolve().parents[3]


def schedule(state, hour, minute):
    require(0 <= hour <= 23 and 0 <= minute <= 59, "invalid_schedule")
    return {
        "Label": "local.resolveflow.backup",
        "ProgramArguments": [
            sys.executable,
            str(Path(__file__).resolve()),
            "--state",
            str(state),
            "scheduled",
        ],
        "WorkingDirectory": str(ROOT / "apps/api"),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "ProcessType": "Background",
        "Umask": 0o077,
        "StandardOutPath": str(state / "schedule.log"),
        "StandardErrorPath": str(state / "schedule-error.log"),
    }


def restore_test(repo, identity):
    state = load_state()
    with admin_connect(state) as conn:
        require(
            Path(conn.execute("SHOW data_directory").fetchone()[0]).resolve() == DATA.resolve(),
            "database_ownership_mismatch",
        )
    target = "resolveflow_test_" + uuid.uuid4().hex
    marker = "resolveflow-backup-" + uuid.uuid4().hex
    with admin_connect(state) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))
        conn.execute(
            sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                sql.Identifier(target), sql.Literal(marker)
            )
        )
    engine = create_engine(
        make_url(url(state, admin=True)).set(database=target),
        poolclass=NullPool,
        hide_parameters=True,
    )
    try:
        with tempfile.TemporaryDirectory(prefix="restore-test-", dir=repo.state) as directory:
            return restore_into(repo, identity, engine, Path(directory) / "restored")
    finally:
        engine.dispose()
        with admin_connect(state) as conn:
            actual = conn.execute(
                "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s",
                (target,),
            ).fetchone()
            require(actual == (marker,), "test_cleanup_ownership_mismatch")
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(target)))


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=ROOT / ".local/backup-control")
    parser.add_argument(
        "command",
        choices=[
            "init",
            "create",
            "scheduled",
            "list",
            "verify",
            "status",
            "failures",
            "restore-test",
            "retention",
            "schedule",
        ],
    )
    parser.add_argument("--repository", type=Path, default=ROOT / ".local/encrypted-backups")
    parser.add_argument("--quiesced", action="store_true")
    parser.add_argument("--snapshot", default="latest")
    parser.add_argument("--apply-retention", action="store_true")
    parser.add_argument("--hour", type=int, default=3)
    parser.add_argument("--minute", type=int, default=0)
    args = parser.parse_args()
    try:
        safe_path(args.state)
        if args.command == "init":
            for destination in (args.state, args.repository):
                if destination.is_relative_to(ROOT):
                    require(
                        subprocess.run(
                            ["git", "check-ignore", "-q", str(destination)], cwd=ROOT
                        ).returncode
                        == 0,
                        "backup_destination_must_be_git_ignored",
                    )
            initialize(
                args.state, args.repository, ROOT / ".local/native/restic-0.19.1/restic", BIN
            )
            print(
                json.dumps(
                    {
                        "initialized": True,
                        "encrypted": True,
                        "off_host_verified": False,
                        "key_recovery_copy_required": True,
                    }
                )
            )
            return 0
        with exclusive(args.state):
            repo = Repository(args.state)
            if args.command in {"create", "scheduled"}:
                require(
                    args.quiesced or args.command == "scheduled",
                    "maintenance_confirmation_required",
                )
                state = load_state()
                settings = Settings()
                require(
                    settings.environment == "development" and settings.database_url is not None,
                    "development_configuration_required",
                )
                require(
                    make_url(settings.database_url.get_secret_value()) == make_url(url(state)),
                    "database_configuration_mismatch",
                )
                engine = create_engine(
                    make_url(url(state, admin=True)).set(database="resolveflow_dev"),
                    poolclass=NullPool,
                    hide_parameters=True,
                )
                try:
                    result = capture(
                        repo, engine, settings, quiesced=True, development_directory=DATA
                    )
                finally:
                    engine.dispose()
            elif args.command == "list":
                result = [{"id": s["id"], "time": s["time"]} for s in repo.snapshots()]
            elif args.command == "verify":
                repo.check()
                result = {"integrity": "passed", "recovery_test_is_separate": True}
            elif args.command == "restore-test":
                result = restore_test(repo, args.snapshot)
            elif args.command == "retention":
                result = repo.retention(args.apply_retention)
            elif args.command == "schedule":
                output = args.state / "local.resolveflow.backup.plist"
                require(not output.exists(), "schedule_template_exists")
                output.write_bytes(plistlib.dumps(schedule(args.state, args.hour, args.minute)))
                output.chmod(0o600)
                result = {
                    "template_written": True,
                    "installed": False,
                    "activated": False,
                    "hour": args.hour,
                    "minute": args.minute,
                }
            else:
                result = repo.status()
                if args.command == "failures":
                    result = result.get("failure", {"recorded": False})
            print(json.dumps(result))
            return int(args.command == "status" and result["stale"])
    except (Exception, KeyboardInterrupt) as exc:
        code = (
            "backup_interrupted"
            if isinstance(exc, KeyboardInterrupt)
            else str(exc)
            if isinstance(exc, BackupError)
            else "backup_operation_failed"
        )
        try:
            private(args.state, directory=True)
            if code != "backup_operation_busy":
                with exclusive(args.state):
                    path = args.state / "status.json"
                    data = json.loads(path.read_text()) if path.exists() else {}
                    data["failure"] = {"at": time.time(), "operation": args.command, "code": code}
                    save_json(path, data)
        except Exception:
            pass
        print(json.dumps({"ok": False, "code": code}), file=sys.stderr)
        return 1


def interrupted(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
