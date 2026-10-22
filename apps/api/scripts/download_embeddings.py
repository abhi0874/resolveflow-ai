"""Explicit one-time official snapshot download; no arbitrary model URL or code."""

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from huggingface_hub import hf_hub_download

from resolveflow.core.config import Settings
from resolveflow.retrieval.contracts import MODEL_ID, REVISION
from resolveflow.retrieval.provider import FILES, verify_snapshot


def download(root: Path):
    if root.exists():
        verify_snapshot(root)
        print("Pinned embedding snapshot already verified")
        return
    root.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    stage = Path(tempfile.mkdtemp(prefix=".embedding-", dir=root.parent))
    try:
        checksums = {}
        for name in FILES:
            path = Path(hf_hub_download(MODEL_ID, name, revision=REVISION, local_dir=stage))
            os.chmod(path, 0o600)
            with path.open("rb") as file:
                checksums[name] = hashlib.file_digest(file, "sha256").hexdigest()
        (stage / "manifest.json").write_text(
            json.dumps({"revision": REVISION, "files": checksums}, indent=2)
        )
        verify_snapshot(stage)
        stage.rename(root)
        print("Pinned local embedding snapshot downloaded and verified")
    finally:
        if stage.exists():
            shutil.rmtree(stage)


if __name__ == "__main__":
    download(Settings().embedding_model_root)
