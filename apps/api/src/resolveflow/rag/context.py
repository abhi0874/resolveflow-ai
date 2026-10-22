"""Shared deterministic RAG preparation, used by direct drafting and graph workers."""

from resolveflow.ai.contracts import AIError
from resolveflow.rag.prompt import ACCOUNT_STATUS, INJECTION, SENSITIVE
from resolveflow.retrieval.contracts import fingerprint


def input_reason(title: str, description: str) -> str | None:
    content = title + "\n" + description
    if ACCOUNT_STATUS.search(content):
        return (
            "Account or payment status requires an authorized human check; "
            "policy text is not proof."
        )
    if INJECTION.search(content):
        return "The request contains instructions that require human review."
    if SENSITIVE.search(content):
        raise AIError("sensitive_input")
    return None


def select_context(results: list[dict], settings) -> tuple[list[dict], str | None]:
    evidence, seen, used = [], set(), 0
    for item in results[: settings.ai_top_k]:
        content = item["content"]
        digest = fingerprint(content)
        if digest in seen or INJECTION.search(content) or SENSITIVE.search(content):
            continue
        if used + len(content) <= settings.ai_context_chars:
            evidence.append(item)
            seen.add(digest)
            used += len(content)
    reason = (
        None if evidence else "No suitable indexed evidence met retrieval and safety requirements."
    )
    return evidence, reason
