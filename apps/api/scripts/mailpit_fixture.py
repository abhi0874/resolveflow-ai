"""Owned loopback-only Mailpit inbox, no relay or external update checks."""

import os
import socket
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
BINARY = ROOT / ".local/native/mailpit-1.32.0/mailpit"


@contextmanager
def isolated_mailpit():
    if not BINARY.is_file():
        raise RuntimeError("Install the pinned local Mailpit inbox; see docs/EMAIL_DELIVERY.md")
    sockets = [socket.socket(), socket.socket()]
    try:
        for sock in sockets:
            sock.bind(("127.0.0.1", 0))
        smtp, http = [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()
    with tempfile.TemporaryDirectory(prefix="resolveflow-mailpit-") as directory:
        # Do not inherit MP_* relay/webhook/provider configuration from the operator.
        env = {"PATH": os.environ.get("PATH", ""), "TMPDIR": directory}
        with open(Path(directory) / "mailpit.log", "w") as log:
            process = subprocess.Popen(
                [
                    str(BINARY),
                    "--smtp",
                    f"127.0.0.1:{smtp}",
                    "--listen",
                    f"127.0.0.1:{http}",
                    "--database",
                    str(Path(directory) / "inbox.db"),
                    "--disable-version-check",
                    "--max",
                    "100",
                    "--max-message-size",
                    "1",
                    "--quiet",
                    "--allowed-hosts",
                    "127.0.0.1,localhost",
                    "--block-remote-css-and-fonts",
                ],
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Owned Mailpit failed to start")
                    try:
                        with urlopen(f"http://127.0.0.1:{http}/readyz", timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        time.sleep(0.05)
                else:
                    raise RuntimeError("Owned Mailpit startup timed out")
                yield smtp, f"http://127.0.0.1:{http}"
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
