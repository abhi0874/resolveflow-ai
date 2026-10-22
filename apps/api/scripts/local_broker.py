"""Manage only ResolveFlow's private loopback Valkey service; no global installation."""

import argparse
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

from redis import Redis

ROOT = Path(__file__).resolve().parents[3]

DIRECTORY = ROOT / ".local/valkey"
BINARY = ROOT / ".local/native/valkey-9.1.2/src/valkey-server"
PORT = 56379


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["setup", "start", "status", "stop"])
    args = parser.parse_args()
    marker = DIRECTORY / "owner.json"
    if args.command == "setup" and not marker.exists():
        if DIRECTORY.exists():
            raise RuntimeError("Existing unmarked directory; refusing setup")
        env = ROOT / "apps/api/.env"
        if "RESOLVEFLOW_REDIS_URL=" in (env.read_text() if env.exists() else ""):
            raise RuntimeError("Existing broker URL preserved; reconcile it manually")
        DIRECTORY.mkdir(mode=0o700)
        state = dict(directory=str(DIRECTORY), port=PORT, password=secrets.token_urlsafe(32))
        marker.write_text(json.dumps(state))
        marker.chmod(0o600)
        config = DIRECTORY / "valkey.conf"
        config.write_text(f'''bind 127.0.0.1
port {PORT}
protected-mode yes
requirepass {state["password"]}
dir "{DIRECTORY}"
pidfile "{DIRECTORY / "valkey.pid"}"
logfile "{DIRECTORY / "server.log"}"
daemonize yes
appendonly yes
appendfsync everysec
maxmemory 128mb
maxmemory-policy noeviction
''')
        config.chmod(0o600)
        # Keep broker credentials separate from the API key; append one new setting only.
        env = ROOT / "apps/api/.env"
        if "RESOLVEFLOW_REDIS_URL=" in env.read_text():
            raise RuntimeError("Existing broker URL preserved; reconcile it manually")
        with env.open("a") as stream:
            stream.write(
                f"\nRESOLVEFLOW_REDIS_URL=redis://:{state['password']}@127.0.0.1:{PORT}/0\n"
            )
        env.chmod(0o600)
    state = json.loads(marker.read_text())
    if state["directory"] != str(DIRECTORY) or state["port"] != PORT:
        raise RuntimeError("Broker ownership mismatch")
    if args.command == "setup":
        secret = DIRECTORY / "docker-password"
        with open(secret, "w", opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
            stream.write(state["password"] + "\n")
        secret.chmod(0o600)
    broker = Redis(
        host="127.0.0.1",
        port=PORT,
        password=state["password"],
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    if args.command in {"setup", "start"}:
        try:
            broker.ping()
        except Exception:
            import socket

            with socket.socket() as probe:
                probe.bind(("127.0.0.1", PORT))  # Never start over another listener.
            subprocess.run([str(BINARY), str(DIRECTORY / "valkey.conf")], check=True)
    if broker.config_get("dir").get("dir") != str(DIRECTORY):
        raise RuntimeError("Unexpected broker; refusing operation")
    if args.command == "stop":
        broker.shutdown(save=True)
        print("ResolveFlow Valkey stopped; data preserved.")
    else:
        print(f"ResolveFlow Valkey ready on 127.0.0.1:{PORT}; authenticated, AOF enabled.")
    broker.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            "Broker command failed; check owned config, binary and port. Credentials hidden.",
            file=sys.stderr,
        )
        sys.exit(1)
