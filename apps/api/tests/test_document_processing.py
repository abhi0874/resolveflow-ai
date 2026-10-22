import subprocess
import sys
import time
import uuid

import pytest
from document_fixtures import pdf_bytes

from resolveflow.core.config import Settings
from resolveflow.documents.chunking import chunk_pages, normalize
from resolveflow.documents.extraction import ProcessingError, extract
from resolveflow.documents.storage import LocalFileStorage
from resolveflow.documents.validation import validate_upload


def config(**values):
    return Settings(_env_file=None, **values)


def test_chunking_determinism_overlap_pages_and_offsets():
    doc = uuid.uuid4()
    pages = [
        {"text": "First paragraph. " * 40 + "\n\n" + "Second paragraph. " * 40, "page_number": 1},
        {"text": "Last page.", "page_number": 2},
        {"text": "  ", "page_number": 3},
    ]
    result = chunk_pages(doc, pages, 200, 30)
    assert result == chunk_pages(doc, pages, 200, 30)
    assert [c.index for c in result] == list(range(len(result)))
    assert len({c.id for c in result}) == len(result)
    assert result[-1].page_number == 2
    for c in result:
        assert 0 < len(c.content) <= 200
        assert normalize(pages[c.page_number - 1]["text"])[c.start : c.end] == c.content
    assert result[1].start < result[0].end
    assert len(chunk_pages(doc, [{"text": "x" * 2000, "page_number": None}], 100, 99)) < 2000
    for size, overlap in [(100, 100), (100, -1), (0, 0)]:
        with pytest.raises(ValueError):
            chunk_pages(doc, pages, size, overlap)
    with pytest.raises(ValueError):
        config(document_chunk_size=100, document_chunk_overlap=100)


@pytest.mark.parametrize(
    "mime,data,expected",
    [
        ("application/pdf", pdf_bytes(("Page one", "Page two")), "Page one"),
        ("text/plain", "Unicode café".encode(), "Unicode café"),
        ("text/plain", "UTF16 text".encode("utf-16"), "UTF16 text"),
        (
            "text/markdown",
            b"# Handbook\n\n**Keep meaning** <script>untrusted</script>",
            "# Handbook",
        ),
    ],
)
def test_real_extraction(mime, data, expected):
    pages = extract(data, mime, config())
    assert expected in pages[0]["text"]
    assert pages[0]["page_number"] == (1 if mime == "application/pdf" else None)


@pytest.mark.parametrize(
    "data,code",
    [
        (b"%PDF-1.7 broken", "invalid_pdf"),
        (pdf_bytes(("",)), "no_text"),
        (pdf_bytes(encrypted=True), "encrypted_pdf"),
    ],
)
def test_pdf_errors_are_safe(data, code):
    with pytest.raises(ProcessingError) as failure:
        extract(data, "application/pdf", config())
    assert failure.value.code == code


def test_extraction_page_and_text_limits():
    with pytest.raises(ProcessingError, match="resource_limit"):
        extract(pdf_bytes(("One", "Two")), "application/pdf", config(document_max_pages=1))
    with pytest.raises(ProcessingError, match="resource_limit"):
        extract(b"x" * 1001, "text/plain", config(document_max_chars=1000))


@pytest.mark.parametrize(
    "script",
    [
        "import time; time.sleep(5)",
        "import time; data=bytearray(150*1024**2); time.sleep(5)",
    ],
)
def test_parser_process_time_and_memory_termination(monkeypatch, script):
    original = subprocess.Popen

    def launch(*args, **kwargs):
        return original([sys.executable, "-I", "-c", script], **kwargs)

    monkeypatch.setattr("resolveflow.documents.extraction.subprocess.Popen", launch)
    started = time.monotonic()
    with pytest.raises(ProcessingError, match="resource_limit"):
        extract(b"test", "text/plain", config(document_timeout_seconds=1, document_memory_mb=64))
    assert time.monotonic() - started < 3


def test_storage_private_paths_symlinks_and_idempotent_delete(tmp_path):
    storage = LocalFileStorage(tmp_path / "private")
    wid, key = uuid.uuid4(), uuid.uuid4().hex
    storage.save(wid, key, b"private")
    assert storage.read(wid, key, 100) == b"private" and storage.exists(wid, key)
    assert (storage.root / wid.hex / key).stat().st_mode & 0o777 == 0o600
    assert storage.root.stat().st_mode & 0o777 == 0o700
    with pytest.raises(ValueError):
        storage.read(wid, "../secret", 100)
    with pytest.raises(OSError):
        storage.read(wid, key, 1)
    other = uuid.uuid4()
    (storage.root / other.hex).symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(OSError):
        storage.save(other, key, b"escape")
    storage.delete(wid, key)
    storage.delete(wid, key)
    assert not storage.exists(wid, key)
    (storage.root / wid.hex / key).symlink_to(tmp_path / "outside")
    with pytest.raises(OSError):
        storage.read(wid, key, 100)
    assert not (tmp_path / "outside").exists()


@pytest.mark.parametrize(
    "name,data",
    [
        ("../file.txt", b"text"),
        ("..%2Ffile.txt", b"text"),
        ("C:\\file.txt", b"text"),
        ("bad%00.txt", b"text"),
        ("script.exe", b"MZ"),
        ("fake.pdf", b"hello"),
        ("fake.txt", b"%PDF-1.7"),
        ("binary.md", b"\x00\x01"),
        ("wrong.txt", b"\xff"),
    ],
)
def test_upload_validation_rejects_unsafe_content(name, data):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        validate_upload(name, data, 1024)


def test_compressed_pdf_stream_limit():
    data = pdf_bytes(("x" * (9 * 1024**2),), compress=True)
    assert len(data) < 100000
    with pytest.raises(ProcessingError, match="resource_limit"):
        extract(data, "application/pdf", config())


def test_storage_refuses_public_permissions_without_changing_them(tmp_path):
    root = tmp_path / "public-mode"
    root.mkdir(mode=0o755)
    root.chmod(0o755)
    with pytest.raises(OSError):
        LocalFileStorage(root).save(uuid.uuid4(), uuid.uuid4().hex, b"data")
    assert root.stat().st_mode & 0o777 == 0o755
