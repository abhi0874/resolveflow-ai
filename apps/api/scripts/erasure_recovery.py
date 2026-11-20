"""Operate the independent deletion records offline. No serving or promotion command."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from resolveflow.backups.erasure_recovery import reconcile
from resolveflow.core.config import Settings
from resolveflow.services.erasure_journal import current_seal, initialize, seal_interrupted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for action in ("initialize", "seal-interrupted", "current-seal"):
        actions.add_parser(action)
    actions.add_parser("reconcile").add_argument("--expected-seal", required=True)
    args = parser.parse_args()
    settings = Settings()
    engine = create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    try:
        if args.action == "reconcile":
            result = reconcile(engine, settings, args.expected_seal)
            print(json.dumps(result))
            return 1 if result["private_file_holds"] else 0
        else:
            with Session(engine) as db:
                if args.action == "initialize":
                    initialize(db, settings)
                elif args.action == "seal-interrupted":
                    seal_interrupted(db, settings)
                else:
                    print(current_seal(db, settings))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(
            "Erasure operation refused. Keep the target offline and inspect protected records."
        )
