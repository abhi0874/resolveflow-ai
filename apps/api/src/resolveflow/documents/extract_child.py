"""One bounded parser process; input bytes only, no application settings or credentials."""

import io
import json
import logging
import resource
import sys


def main():
    mime, page_limit, char_limit, seconds, memory_mb = sys.argv[1:]
    page_limit, char_limit = int(page_limit), int(char_limit)
    seconds, memory_mb = int(seconds), int(memory_mb)
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (memory_mb * 1024**2, memory_mb * 1024**2))
    logging.disable(logging.CRITICAL)
    data = sys.stdin.buffer.read(5 * 1024**2 + 1)
    if len(data) > 5 * 1024**2:
        return {"error": "resource_limit"}
    pages = []
    if mime == "application/pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted:
                return {"error": "encrypted_pdf"}
            if len(reader.pages) > page_limit:
                return {"error": "resource_limit"}
            total = 0
            for number, page in enumerate(reader.pages, 1):
                stream = page.get_contents()
                if stream and len(stream.get_data()) > 8 * 1024**2:
                    return {"error": "resource_limit"}
                text = page.extract_text() or ""
                total += len(text)
                if total > char_limit:
                    return {"error": "resource_limit"}
                pages.append({"page_number": number, "text": text})
        except MemoryError:
            return {"error": "resource_limit"}
        except Exception:
            return {"error": "invalid_pdf"}
    else:
        try:
            text = data.decode(
                "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
            )
        except UnicodeError:
            return {"error": "invalid_encoding"}
        if len(text) > char_limit:
            return {"error": "resource_limit"}
        pages.append({"page_number": None, "text": text})
    if not any(page["text"].strip() for page in pages):
        return {"error": "no_text"}
    return {"pages": pages}


if __name__ == "__main__":
    try:
        result = main()
    except MemoryError:
        result = {"error": "resource_limit"}
    except Exception:
        result = {"error": "extraction_failed"}
    sys.stdout.write(json.dumps(result))
