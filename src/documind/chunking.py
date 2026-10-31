"""Split page text into deterministic, overlapping chunks."""

from __future__ import annotations

import re

from documind.models import Chunk, Page

# Use the strongest available natural boundary before falling back to whitespace.
_BOUNDARY_PATTERNS = (
    re.compile(r"\n{2,}"),
    re.compile(r"(?<=[.!?])\s+"),
    re.compile(r"\s+"),
)


def _next_chunk_end(text: str, start: int, max_size: int) -> int:
    """Choose a paragraph, sentence, or word boundary within the size limit."""
    limit = min(start + max_size, len(text))
    if limit == len(text):
        return limit

    for pattern in _BOUNDARY_PATTERNS:
        boundaries = [match.end() for match in pattern.finditer(text, start, limit)]
        if boundaries:
            return boundaries[-1]

    raise ValueError(
        f"A word longer than chunk_size={max_size} cannot be split without breaking the word"
    )


def _split_page(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split one page and carry a word-aligned suffix into the next chunk."""
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = _next_chunk_end(text, start, chunk_size)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(text):
            break

        # Move the next start back by the requested overlap, then avoid starting
        # halfway through a word. The chunk IDs remain based on output order.
        next_start = max(start + 1, end - overlap)
        if next_start > 0 and not text[next_start - 1].isspace():
            next_space = re.search(r"\s", text[next_start:end])
            if next_space is None:
                next_start = end
            else:
                next_start += next_space.end()
        start = next_start

    return chunks


def chunk_pages(
    pages: list[Page],
    doc_hash: str,
    filename: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[Chunk]:
    """Chunk pages and assign stable IDs from the document hash and sequence."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    if not doc_hash:
        raise ValueError("doc_hash must not be empty")

    chunks: list[Chunk] = []
    for page in pages:
        for page_text in _split_page(page.text, chunk_size, overlap):
            chunk_index = len(chunks)
            chunks.append(
                Chunk(
                    id=f"{doc_hash}:{chunk_index}",
                    doc_id=doc_hash,
                    filename=filename,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    text=page_text,
                )
            )
    return chunks
