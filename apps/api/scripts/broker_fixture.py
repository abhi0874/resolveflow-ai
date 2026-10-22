"""Disposable, authenticated Valkey process for integration/browser tests only."""

import secrets
import socket
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from redis import Redis

ROOT = Path(__file__).resolve().parents[3]
BINARY = ROOT / ".local/native/valkey-9.1.2/src/valkey-server"


@contextmanager
def isolated_broker():
    if not BINARY.is_file():
        raise RuntimeError("Install the local broker with scripts/install_broker.py first")
    with tempfile.TemporaryDirectory(prefix="resolveflow-test-broker-") as directory:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        password = secrets.token_urlsafe(24)
        config = Path(directory) / "valkey.conf"
        config.write_text(
            f"bind 127.0.0.1\nport {port}\nprotected-mode yes\n"
            f'requirepass {password}\ndir "{directory}"\nsave ""\n'
            "appendonly no\nmaxmemory 64mb\nmaxmemory-policy noeviction\n"
        )
        config.chmod(0o600)
        broker = Redis(
            host="127.0.0.1",
            port=port,
            password=password,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        with (Path(directory) / "log").open("w") as log:
            process = subprocess.Popen([str(BINARY), str(config)], stdout=log, stderr=log)
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Isolated broker failed to start")
                    try:
                        if broker.ping():
                            break
                    except Exception:
                        time.sleep(0.05)
                else:
                    raise RuntimeError("Isolated broker startup timeout")
                yield f"redis://:{password}@127.0.0.1:{port}/0", process
            finally:
                broker.close()
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
