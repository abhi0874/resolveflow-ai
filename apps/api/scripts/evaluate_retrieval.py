"""Evaluate in the existing ownership-checked disposable test database harness."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from local_db import API, load_state, url

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "TEST_DATABASE_ADMIN_URL": url(load_state(), admin=True),
        "RETRIEVAL_EVALUATION_OUTPUT": str(output),
    }
    raise SystemExit(
        subprocess.run(
            [sys.executable, "-m", "pytest", "--run-db", "tests/test_retrieval_evaluation.py"],
            cwd=API,
            env=env,
        ).returncode
    )
