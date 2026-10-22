"""Manage only this project's native, password-protected PostgreSQL cluster."""

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "apps/api"
BIN = ROOT / ".local/native/Postgres.app/Contents/Versions/18/bin"
DATA = ROOT / "data/local/postgresql18"
STATE = ROOT / ".local/database.json"
PORT = 55433


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run([str(BIN / args[0]), *args[1:]], check=check)


def load_state() -> dict:
    state = json.loads(STATE.read_text())
    if state["data_directory"] != str(DATA) or state["port"] != PORT:
        raise RuntimeError("Cluster marker does not match this checkout; refusing operation")
    return state


def admin_connect(state: dict, database: str = "postgres") -> psycopg.Connection:
    return psycopg.connect(
        host="127.0.0.1",
        port=PORT,
        user="resolveflow_admin",
        password=state["admin_password"],
        dbname=database,
        connect_timeout=3,
        autocommit=True,
    )


def url(state: dict, *, admin: bool = False) -> str:
    return URL.create(
        "postgresql+psycopg",
        host="127.0.0.1",
        port=PORT,
        username="resolveflow_admin" if admin else "resolveflow_dev",
        password=state["admin_password" if admin else "dev_password"],
        database="postgres" if admin else "resolveflow_dev",
    ).render_as_string(hide_password=False)


def start() -> None:
    load_state()
    if not (DATA / "PG_VERSION").exists() or (DATA / "PG_VERSION").read_text().strip() != "18":
        raise RuntimeError("Expected initialized PostgreSQL 18 cluster; refusing operation")
    if run("pg_ctl", "-D", str(DATA), "status", check=False).returncode == 0:
        return
    run("pg_ctl", "-D", str(DATA), "-l", str(DATA / "server.log"), "-w", "start")


def setup() -> None:
    if not (BIN / "initdb").is_file():
        raise RuntimeError("Native PostgreSQL bundle missing; see docs/DATABASE.md")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    if not STATE.exists():
        if DATA.exists():
            raise RuntimeError(
                "Existing data directory has no ownership marker; refusing to change it"
            )
        state = {
            "data_directory": str(DATA),
            "port": PORT,
            "admin_password": secrets.token_urlsafe(32),
            "dev_password": secrets.token_urlsafe(32),
        }
        with open(STATE, "x", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
            json.dump(state, stream)
    state = load_state()
    if not DATA.exists():
        DATA.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", prefix="resolveflow-pg-") as pwfile:
            pwfile.write(state["admin_password"] + "\n")
            pwfile.flush()
            run(
                "initdb",
                "-D",
                str(DATA),
                "--username=resolveflow_admin",
                f"--pwfile={pwfile.name}",
                "--auth=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
            )
        with (DATA / "postgresql.conf").open("a") as config:
            config.write(
                "\n# ResolveFlow project-local cluster\n"
                f"listen_addresses = '127.0.0.1'\nport = {PORT}\n"
                "unix_socket_directories = ''\npassword_encryption = 'scram-sha-256'\n"
            )
    start()
    with admin_connect(state) as conn:
        actual = conn.execute("SHOW data_directory").fetchone()[0]
        if Path(actual).resolve() != DATA.resolve():
            raise RuntimeError("Unexpected server on local port; refusing to modify it")
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'resolveflow_dev'").fetchone():
            conn.execute(
                sql.SQL(
                    "CREATE ROLE resolveflow_dev LOGIN PASSWORD {} "
                    "NOSUPERUSER NOCREATEDB NOCREATEROLE"
                ).format(sql.Literal(state["dev_password"]))
            )
        if not conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'resolveflow_dev'"
        ).fetchone():
            conn.execute("CREATE DATABASE resolveflow_dev OWNER resolveflow_dev")
    # vector is untrusted: bootstrap with cluster admin, then migrate as the app owner.
    with admin_connect(state, "resolveflow_dev") as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
    envfile = API / ".env"
    existing = envfile.read_text() if envfile.exists() else ""
    if any(re.match(r"\s*(?:export\s+)?DATABASE_URL\s*=", line) for line in existing.splitlines()):
        print(
            "Existing DATABASE_URL preserved; verify it targets your intended development database."
        )
    else:
        with open(envfile, "a", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
            stream.write(f"\nDATABASE_URL={url(state)}\n")
        envfile.chmod(0o600)
        print(
            "Development DATABASE_URL written to ignored apps/api/.env (credentials not displayed)."
        )
    print(f"Cluster ready on 127.0.0.1:{PORT}. Run alembic upgrade head explicitly.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "start", "stop", "status", "test", "psql"])
    args = parser.parse_args()
    if args.command == "setup":
        setup()
        return
    state = load_state()
    if args.command == "start":
        start()
    elif args.command == "stop":
        run("pg_ctl", "-D", str(DATA), "-m", "fast", "-w", "stop")
    elif args.command == "status":
        run("pg_ctl", "-D", str(DATA), "status")
        with admin_connect(state, "resolveflow_dev") as conn:
            print("PostgreSQL:", conn.execute("SHOW server_version").fetchone()[0])
            print(
                "pgvector:",
                conn.execute(
                    "SELECT extversion FROM pg_extension WHERE extname='vector'"
                ).fetchone()[0],
            )
    elif args.command == "test":
        env = {**os.environ, "TEST_DATABASE_ADMIN_URL": url(state, admin=True)}
        result = subprocess.run([sys.executable, "-m", "pytest", "--run-db"], cwd=API, env=env)
        sys.exit(result.returncode)
    else:
        env = {**os.environ, "PGPASSWORD": state["dev_password"]}
        result = subprocess.run(
            [
                str(BIN / "psql"),
                "-h",
                "127.0.0.1",
                "-p",
                str(PORT),
                "-U",
                "resolveflow_dev",
                "-d",
                "resolveflow_dev",
            ],
            env=env,
        )
        sys.exit(result.returncode)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except (OSError, psycopg.Error, subprocess.CalledProcessError) as exc:
        # Connection errors may include DSNs; keep credentials out of console logs.
        print(
            f"Local database command failed ({type(exc).__name__}). See docs/DATABASE.md.",
            file=sys.stderr,
        )
        sys.exit(1)
