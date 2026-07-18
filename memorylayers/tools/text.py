"""Word-level text handling for duplicate detection and full-text queries."""

import re

_STOP_WORDS = frozenset(
    "a an and are as at be been but by for from had has have he her his i in is it its me my of on or our she so that the their them they this to was we were will with you your user".split()
)


def words(*, text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def content_tokens(*, text: str) -> frozenset[str]:
    return frozenset(word for word in words(text=text) if len(word) > 1 and word not in _STOP_WORDS)


def jaccard(*, a: frozenset[str], b: frozenset[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def fts_query(*, text: str) -> str | None:
    """An FTS5 query matching any content token, or None when there are none."""
    tokens = sorted(content_tokens(text=text))
    return " OR ".join(f'"{token}"' for token in tokens) or None
