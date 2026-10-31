"""Shared data models used by the document pipeline."""

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


@dataclass(frozen=True)
class SearchResult:
    """A retrieved chunk with normalized similarity and its one-based rank."""

    chunk: Chunk
    score: float
    rank: int


@dataclass(frozen=True)
class Document:
    """A document tracked in the local SQLite registry."""

    id: str
    filename: str
    sha256: str
    pages: int
    chunk_count: int
    created_at: str


@dataclass(frozen=True)
class Answer:
    """Generated or retrieval-only response with cited source passages."""

    text: str
    sources: list[SearchResult]
    model_name: str | None
    refused: bool
