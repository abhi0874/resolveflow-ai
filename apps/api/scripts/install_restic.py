"""Install a pinned official restic release inside this checkout; no global tools."""

import bz2
import hashlib
import platform
import subprocess
from pathlib import Path


def fetch(url):
    return subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--proto",
            "=https",
            "--tlsv1.2",
            "--max-time",
            "120",
            url,
        ],
        capture_output=True,
        check=True,
    ).stdout


VERSION = "0.19.1"
ROOT = Path(__file__).resolve().parents[3]


def main():
    system = {"Darwin": "darwin", "Linux": "linux"}[platform.system()]
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}[platform.machine()]
    name = f"restic_{VERSION}_{system}_{arch}.bz2"
    base = f"https://github.com/restic/restic/releases/download/v{VERSION}"
    directory = ROOT / ".local/native" / f"restic-{VERSION}"
    if directory.exists():
        raise RuntimeError("Destination exists; refusing replacement")
    sums = fetch(base + "/SHA256SUMS").decode()
    expected = next(line.split()[0] for line in sums.splitlines() if line.endswith(name))
    archive = fetch(base + "/" + name)
    if hashlib.sha256(archive).hexdigest() != expected:
        raise RuntimeError("Official checksum mismatch")
    license_text = fetch(f"https://raw.githubusercontent.com/restic/restic/v{VERSION}/LICENSE")
    directory.mkdir(mode=0o700, parents=True)
    binary = directory / "restic"
    binary.write_bytes(bz2.decompress(archive))
    binary.chmod(0o700)
    (directory / "LICENSE").write_bytes(license_text)
    (directory / "SHA256SUMS").write_text(sums)
    print(f"Installed restic {VERSION}; SHA-256 verified; BSD-2-Clause license retained.")


if __name__ == "__main__":
    main()
