"""Pydantic request and response models for the local API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from documind.models import Chunk, Document, SearchResult


class HealthResponse(BaseModel):
    """Simple health status."""

    status: str = "ok"


class DocumentResponse(BaseModel):
    """Public fields for an indexed document."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    sha256: str
    pages: int
    chunk_count: int
    created_at: str

    @classmethod
    def from_document(cls, document: Document) -> DocumentResponse:
        """Convert the internal document record to the API response."""
        return cls.model_validate(document)


class SearchRequest(BaseModel):
    """Search input."""

    query: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=100)


class PassageResponse(BaseModel):
    """One retrieved passage with a file and page citation."""

    id: str
    filename: str
    page_number: int
    text: str
    score: float
    rank: int

    @classmethod
    def from_result(cls, result: SearchResult) -> PassageResponse:
        """Convert a retrieved chunk to its public representation."""
        chunk: Chunk = result.chunk
        return cls(
            id=chunk.id,
            filename=chunk.filename,
            page_number=chunk.page_number,
            text=chunk.text,
            score=result.score,
            rank=result.rank,
        )


class SearchResponse(BaseModel):
    """Ordered passages returned for a query."""

    query: str
    results: list[PassageResponse]
    no_relevant_passage: bool




