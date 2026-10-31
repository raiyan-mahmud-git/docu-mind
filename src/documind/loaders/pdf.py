"""PDF loader using PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from documind.loaders.cleaning import clean_text
from documind.models import Page


def load_pdf(path: str | Path) -> list[Page]:
    """Load non-empty PDF pages, preserving their original one-based numbers."""
    source = Path(path)
    try:
        document = fitz.open(source)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"Could not open PDF {source}: {exc}") from exc

    if document.is_encrypted:
        document.close()
        raise ValueError(f"PDF {source} is password-protected")

    pages: list[Page] = []
    try:
        for page_index in range(len(document)):
            pdf_page: fitz.Page = document.load_page(page_index)
            text = clean_text(pdf_page.get_text())
            if text:
                pages.append(Page(text=text, page_number=page_index + 1))
    except (RuntimeError, ValueError) as exc:
        raise ValueError(f"Could not read PDF {source}: {exc}") from exc
    finally:
        document.close()

    if not pages:
        raise ValueError(f"PDF {source} contains no extractable text")
    return pages
