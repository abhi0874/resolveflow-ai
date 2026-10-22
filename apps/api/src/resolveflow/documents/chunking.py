import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    id: uuid.UUID
    index: int
    content: str
    page_number: int | None
    start: int
    end: int


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(c for c in text if not unicodedata.category(c).startswith("C") or c in "\n\t")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.rstrip() for line in text.splitlines())).strip()


def chunk_pages(
    document_id: uuid.UUID, pages: list[dict], size: int, overlap: int, maximum: int = 2000
) -> list[Chunk]:
    if not 0 <= overlap < size or size < 100:
        raise ValueError("Invalid chunk configuration")
    result = []
    for page in pages:
        text = normalize(page["text"])
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                floor = start + max(size // 2, overlap + 1)
                boundary = text.rfind("\n\n", floor, end)
                if boundary < 0:
                    boundary = text.rfind(" ", floor, end)
                if boundary > floor:
                    end = boundary
            raw = text[start:end]
            content = raw.strip()
            if content:
                index = len(result)
                digest = hashlib.sha256(content.encode()).hexdigest()
                result.append(
                    Chunk(
                        uuid.uuid5(document_id, f"v1:{index}:{digest}"),
                        index,
                        content,
                        page["page_number"],
                        start + len(raw) - len(raw.lstrip()),
                        end - len(raw) + len(raw.rstrip()),
                    )
                )
                if len(result) > maximum:
                    raise ValueError("Too many chunks")
            if end == len(text):
                break
            start = max(start + 1, end - overlap)
    return result
