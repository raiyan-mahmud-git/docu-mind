"""PDF loader using PyMuPDF with a local OCR fallback for image-based pages."""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path

import pymupdf as fitz

from documind.loaders.cleaning import clean_text
from documind.models import Page

logger = logging.getLogger(__name__)
_MIN_TEXT_BEFORE_OCR = 40


def _find_tessdata() -> Path | None:
    """Locate Tesseract language files from config, PATH, or common Windows folders."""
    configured_path = os.getenv("DOCUMIND_OCR_TESSDATA") or os.getenv("TESSDATA_PREFIX")
    candidates: list[Path] = [Path(configured_path)] if configured_path else []
    executable = shutil.which("tesseract")
    if executable:
        candidates.append(Path(executable).resolve().parent / "tessdata")
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        program_files = os.getenv(variable)
        if program_files:
            candidates.append(Path(program_files) / "Tesseract-OCR" / "tessdata")
    for candidate in candidates:
        if (candidate / "eng.traineddata").is_file():
            return candidate
    return None


def _ocr_page(
    pdf_page: fitz.Page,
    language: str,
    dpi: int,
    tessdata: Path | None,
    full: bool = False,
) -> str:
    """OCR page image regions and return their recognized text."""
    tessdata = tessdata or _find_tessdata()
    text_page = pdf_page.get_textpage_ocr(
        language=language,
        dpi=dpi,
        full=full,
        tessdata=str(tessdata) if tessdata is not None else None,
    )
    return str(pdf_page.get_text(textpage=text_page))


def load_pdf(
    path: str | Path,
    *,
    ocr_enabled: bool = True,
    ocr_language: str = "eng",
    ocr_dpi: int = 300,
    ocr_tessdata: Path | None = None,
) -> list[Page]:
    """Load PDF text and OCR pages that contain little extractable text."""
    if ocr_dpi < 72:
        raise ValueError("OCR DPI must be at least 72")
    if not ocr_language.strip():
        raise ValueError("OCR language must not be empty")
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
            has_images = bool(pdf_page.get_images())
            if ocr_enabled and has_images and len(text) < _MIN_TEXT_BEFORE_OCR:
                try:
                    text = clean_text(
                        _ocr_page(pdf_page, ocr_language, ocr_dpi, ocr_tessdata)
                    )
                    if text:
                        logger.info(
                            "OCR extracted text from %s page %d",
                            source.name,
                            page_index + 1,
                        )
                except (OSError, RuntimeError, ValueError) as exc:
                    raise ValueError(
                        f"OCR failed for {source} page {page_index + 1}. "
                        "Install Tesseract OCR and its language data, or set "
                        "DOCUMIND_OCR_TESSDATA to its tessdata folder. "
                        "Set DOCUMIND_OCR_ENABLED=false to skip OCR. "
                        f"Details: {exc}"
                    ) from exc
            if text:
                pages.append(Page(text=text, page_number=page_index + 1))
    except (RuntimeError, ValueError) as exc:
        raise ValueError(f"Could not read PDF {source}: {exc}") from exc
    finally:
        document.close()

    if not pages:
        suffix = " after OCR" if ocr_enabled else ""
        raise ValueError(f"PDF {source} contains no extractable text{suffix}")
    return pages


def _parse_page_selection(selection: str, page_count: int, max_pages: int) -> list[int]:
    """Parse one-based page numbers and inclusive ranges such as ``1,3-5``."""
    if not selection.strip():
        raise ValueError("Enter at least one page number, such as 1 or 2-4")

    selected: list[int] = []
    for part in selection.split(","):
        match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", part)
        if match is None:
            raise ValueError("Use page numbers or ranges separated by commas, such as 1,3-5")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start > end:
            raise ValueError(f"Page range {part.strip()} must go from lower to higher")
        if start < 1 or end > page_count:
            raise ValueError(f"Page numbers must be between 1 and {page_count}")
        selected.extend(range(start, end + 1))

    selected = list(dict.fromkeys(selected))
    if len(selected) > max_pages:
        raise ValueError(f"Choose no more than {max_pages} pages per extraction")
    return selected


def extract_pdf_pages(
    path: str | Path,
    selection: str,
    *,
    ocr_enabled: bool = True,
    ocr_language: str = "eng",
    ocr_dpi: int = 300,
    ocr_tessdata: Path | None = None,
    max_pages: int = 20,
) -> tuple[int, list[Page]]:
    """Extract selectable text or OCR only the pages selected by the user."""
    if ocr_dpi < 72:
        raise ValueError("OCR DPI must be at least 72")
    if not ocr_language.strip():
        raise ValueError("OCR language must not be empty")
    if max_pages < 1:
        raise ValueError("max_pages must be positive")

    source = Path(path)
    try:
        document = fitz.open(source)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"Could not open PDF {source}: {exc}") from exc

    if document.is_encrypted:
        document.close()
        raise ValueError(f"PDF {source} is password-protected")

    try:
        selected_pages = _parse_page_selection(selection, len(document), max_pages)
        extracted: list[Page] = []
        for page_number in selected_pages:
            pdf_page = document.load_page(page_number - 1)
            text = clean_text(pdf_page.get_text())
            if ocr_enabled and len(text) < _MIN_TEXT_BEFORE_OCR:
                try:
                    ocr_text = clean_text(
                        _ocr_page(
                            pdf_page,
                            ocr_language,
                            ocr_dpi,
                            ocr_tessdata,
                            full=True,
                        )
                    )
                    if ocr_text:
                        text = ocr_text
                        logger.info(
                            "OCR extracted copy text from %s page %d",
                            source.name,
                            page_number,
                        )
                except (OSError, RuntimeError, ValueError) as exc:
                    raise ValueError(
                        f"OCR failed for {source} page {page_number}. Install Tesseract "
                        "and its language data, or set DOCUMIND_OCR_TESSDATA. "
                        f"Details: {exc}"
                    ) from exc
            extracted.append(Page(text=text, page_number=page_number))
        return len(document), extracted
    except (RuntimeError, ValueError) as exc:
        raise ValueError(f"Could not extract selected pages from PDF {source}: {exc}") from exc
    finally:
        document.close()
