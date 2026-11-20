"""Run encrypted capture and quarantined restore for disposable staging databases."""

import argparse
import json
import os
import uuid
from pathlib import Path

from resolveflow.backups.repository import Repository, initialize
from resolveflow.backups.safety import BackupError, exclusive, require
from resolveflow.backups.service import capture, restore_into
from resolveflow.core.config import Settings
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


def verified_engine(settings, identifier):
    require(settings.environment == "production", "staging_production_settings_required")
    require(not settings.ai_live_enabled and settings.database_url, "unsafe_staging_settings")
    url = make_url(settings.database_url.get_secret_value())
    require(
        url.drivername == "postgresql+psycopg"
        and url.host == "127.0.0.1"
        and url.port
        and not url.query
        and url.database == f"resolveflow_test_{identifier.hex}",
        "unexpected_staging_database",
    )
    engine = create_engine(url, poolclass=NullPool, hide_parameters=True)
    try:
        with engine.connect() as conn:
            marker = conn.scalar(
                text(
                    "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                    "WHERE datname = current_database()"
                )
            )
        require(marker == f"resolveflow-backup-staging-{identifier.hex}", "staging_marker_mismatch")
    except BaseException:
        engine.dispose()
        raise
    return engine


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    actions = parser.add_subparsers(dest="action", required=True)
    init = actions.add_parser("init")
    init.add_argument("--repository", required=True, type=Path)
    init.add_argument("--restic", required=True, type=Path)
    init.add_argument("--pg-bin", required=True, type=Path)
    save = actions.add_parser("capture")
    save.add_argument("--database-id", required=True, type=uuid.UUID)
    save.add_argument("--quiesced", required=True, action="store_true")
    restore = actions.add_parser("restore")
    restore.add_argument("--database-id", required=True, type=uuid.UUID)
    restore.add_argument("--snapshot", required=True)
    restore.add_argument("--expected-seal", required=True)
    restore.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    if args.action == "init":
        initialize(args.state, args.repository, args.restic, args.pg_bin)
        return
    settings = Settings(_env_file=None)
    engine = verified_engine(settings, args.database_id)
    try:
        with exclusive(args.state):
            repo = Repository(args.state)
            if args.action == "capture":
                result = capture(repo, engine, settings, quiesced=args.quiesced)
            else:
                result = restore_into(
                    repo,
                    args.snapshot,
                    engine,
                    args.destination,
                    settings=settings,
                    expected_seal=args.expected_seal,
                )
        print(json.dumps(result))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except BackupError as exc:
        raise SystemExit(str(exc)) from None
    except Exception:
        raise SystemExit(
            "Staging backup operation failed. Keep any restore target quarantined."
        ) from None
