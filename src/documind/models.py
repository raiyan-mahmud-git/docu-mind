"""Small data models shared by the document pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    """Clean text from one source page; page numbers are one-based."""

    text: str
    page_number: int


@dataclass(frozen=True)
class Chunk:
    """A text passage linked to its source document and page."""

    id: str
    doc_id: str
    filename: str
    page_number: int
    chunk_index: int
    text: str
