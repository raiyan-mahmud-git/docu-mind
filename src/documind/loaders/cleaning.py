"""Shared text cleanup for document loaders."""

from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """Normalize line endings and layout whitespace while preserving paragraphs."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Repair words split at a line ending, such as "docu-\nment".
    text = re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    # A single newline is usually a visual wrap; blank lines mark paragraphs.
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    return text.strip()
