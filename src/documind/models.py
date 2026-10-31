"""Small data models shared by the document pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Page:
    """Clean text from one source page; page numbers are one-based."""

    text: str
    page_number: int
