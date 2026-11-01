"""Image loader that extracts text locally with Tesseract OCR via PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from documind.loaders.cleaning import clean_text
from documind.loaders.pdf import _find_tessdata
from documind.models import Page


def load_image(
    path: str | Path,
    *,
    ocr_enabled: bool = True,
    ocr_language: str = "eng",
    ocr_tessdata: Path | None = None,
) -> list[Page]:
    """OCR a standalone image and return its recognized text as page one."""
    source = Path(path)
    if not ocr_enabled:
        raise ValueError("Image OCR is disabled; set DOCUMIND_OCR_ENABLED=true to read images")
    if not ocr_language.strip():
        raise ValueError("OCR language must not be empty")

    try:
        pixmap = fitz.Pixmap(source)
        if pixmap.alpha:
            pixmap = fitz.Pixmap(pixmap, 0)
        tessdata = ocr_tessdata or _find_tessdata()
        ocr_pdf = pixmap.pdfocr_tobytes(
            language=ocr_language,
            tessdata=str(tessdata) if tessdata is not None else None,
        )
        with fitz.open("pdf", ocr_pdf) as document:
            text = clean_text(document[0].get_text())
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(
            f"OCR failed for image {source}. Install Tesseract and its language data, "
            "or set DOCUMIND_OCR_TESSDATA to the tessdata folder. "
            f"Details: {exc}"
        ) from exc

    if not text:
        raise ValueError(f"No text could be recognized in image {source}")
    return [Page(text=text, page_number=1)]
