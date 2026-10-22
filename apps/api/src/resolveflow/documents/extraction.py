"""Supervise parsing outside the API process. Not a durable background worker."""

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from resolveflow.core.config import Settings
from resolveflow.documents.validation import ERRORS


class ProcessingError(Exception):
    def __init__(self, code: str):
        self.code = code if code in ERRORS else "extraction_failed"
        super().__init__(self.code)


# Per API process, fail fast instead of building an unbounded in-memory queue.
SLOTS = threading.BoundedSemaphore(2)


def extract(data: bytes, mime: str, settings: Settings) -> list[dict]:
    if not SLOTS.acquire(blocking=False):
        raise ProcessingError("resource_limit")
    try:
        return _extract(data, mime, settings)
    finally:
        SLOTS.release()


def _extract(data: bytes, mime: str, settings: Settings) -> list[dict]:
    command = [
        sys.executable,
        "-I",
        str(Path(__file__).with_name("extract_child.py")),
        mime,
        str(settings.document_max_pages),
        str(settings.document_max_chars),
        str(settings.document_timeout_seconds),
        str(settings.document_memory_mb),
    ]
    child = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd="/",
        env={"LANG": "C.UTF-8"},
    )
    output = []
    done = threading.Event()

    def communicate():
        try:
            output.append(child.communicate(data)[0])
        finally:
            done.set()

    thread = threading.Thread(target=communicate, daemon=True)
    thread.start()
    deadline = time.monotonic() + settings.document_timeout_seconds
    try:
        try:
            process = psutil.Process(child.pid)
        except psutil.NoSuchProcess:
            process = None
        while not done.wait(0.02):
            if time.monotonic() > deadline:
                raise ProcessingError("resource_limit")
            try:
                if process and process.memory_info().rss > settings.document_memory_mb * 1024**2:
                    raise ProcessingError("resource_limit")
            except psutil.NoSuchProcess:
                pass
        if child.returncode != 0:
            raise ProcessingError("resource_limit")
        if not output or len(output[0]) > settings.document_max_chars * 8 + 100000:
            raise ProcessingError("resource_limit")
        result = json.loads(output[0])
        if "error" in result:
            raise ProcessingError(result["error"])
        return result["pages"]
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()
        thread.join(timeout=1)
