import unicodedata
from pathlib import PurePath
from urllib.parse import unquote

from fastapi import HTTPException

TYPES = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown"}
ERRORS = {
    "invalid_pdf": "This PDF is damaged or unsupported. Export a new PDF and try again.",
    "encrypted_pdf": "Password-protected PDFs are not supported. Upload an unencrypted copy.",
    "no_text": "No usable text was found. Scanned PDFs require OCR, which is not supported yet.",
    "invalid_encoding": "Use UTF-8 text, or UTF-16 text with a byte-order mark.",
    "resource_limit": "This document exceeds processing limits. Split it into smaller documents.",
    "storage_error": "The file could not be accessed. Retry, or delete and upload it again.",
    "interrupted": "Processing was interrupted. Retry this document.",
    "delete_failed": "File cleanup is incomplete. Retry deletion.",
    "extraction_failed": "Text extraction failed. Try a new export of this document.",
}


def validate_upload(raw_name: str, data: bytes, limit: int) -> tuple[str, str]:
    try:
        name = unicodedata.normalize("NFC", unquote(raw_name, errors="strict")).strip()
    except UnicodeError:
        raise HTTPException(422) from None
    if (
        not name
        or len(name) > 255
        or "/" in name
        or "\\" in name
        or name in {".", ".."}
        or any(unicodedata.category(c).startswith("C") for c in name)
    ):
        raise HTTPException(422)
    ext = PurePath(name).suffix.lower()
    if ext not in TYPES:
        raise HTTPException(415)
    if len(data) > limit:
        raise HTTPException(413)
    if not data:
        raise HTTPException(422)
    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise HTTPException(422)
    else:
        if data.startswith((b"%PDF-", b"PK\x03\x04", b"MZ", b"\x7fELF")):
            raise HTTPException(422)
        try:
            text = decode_text(data)
        except UnicodeError:
            raise HTTPException(422) from None
        if any(ord(c) < 32 and c not in "\n\r\t\f" for c in text):
            raise HTTPException(422)
    return name, TYPES[ext]


def decode_text(data: bytes) -> str:
    return data.decode("utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
