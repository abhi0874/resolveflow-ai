"""Build pinned, checksum-verified Valkey without Homebrew or Docker."""

import hashlib
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
VERSION = "9.1.2"
SHA256 = "19c23908e7d57e8d91ef85b41f5646307582f10f4f0fb999bbf89ed24ec9c983"
URL = f"https://github.com/valkey-io/valkey/archive/refs/tags/{VERSION}.tar.gz"


def main():
    cache = ROOT / ".cache/downloads"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"valkey-{VERSION}.tar.gz"
    if not archive.exists():
        with urlopen(URL, timeout=30) as response:
            archive.write_bytes(response.read(30 * 1024**2))
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise RuntimeError("Valkey source checksum mismatch")
    # Upstream Lua linker flags do not quote paths containing spaces.
    with tempfile.TemporaryDirectory(prefix="resolveflow-valkey-", dir="/private/tmp") as tmp:
        with tarfile.open(archive) as source:
            source.extractall(tmp, filter="data")
        build = Path(tmp) / f"valkey-{VERSION}"
        with (ROOT / ".cache/valkey-build.log").open("w") as log:
            subprocess.run(
                ["make", "-j4", "BUILD_TLS=no"],
                cwd=build,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        target = ROOT / f".local/native/valkey-{VERSION}/src"
        target.mkdir(parents=True, exist_ok=True)
        for name in ("valkey-server", "valkey-cli"):
            shutil.copy2(build / "src" / name, target / name)
    print(f"Valkey {VERSION} built locally; no system service installed.")


if __name__ == "__main__":
    main()
