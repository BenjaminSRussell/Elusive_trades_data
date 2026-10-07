"""Sanitize user-supplied part/model numbers for filesystem paths."""
from __future__ import annotations

import re


_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_part_token(value: str, *, max_len: int = 120, empty: str = "UNKNOWN") -> str:
    """Return a single path segment safe for filenames.

    Rejects path separators, traversal (".."), newlines, and other junk.
    """
    if value is None:
        return empty
    text = str(value).strip()
    if not text or text.isspace():
        return empty
    # Collapse whitespace/newlines first
    text = re.sub(r"\s+", "_", text)
    text = text.replace("/", "_").replace("\\", "_").replace("..", "_")
    text = _SAFE_RE.sub("_", text)
    text = text.strip("._") or empty
    if text in {".", ".."}:
        text = empty
    return text[:max_len]
