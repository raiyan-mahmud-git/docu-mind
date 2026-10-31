from pathlib import Path

import pymupdf as fitz
import pytest

from documind.loaders import load_markdown, load_pdf, load_text
from documind.models import Page


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Create a small three-page PDF with extractable text."""
    path = tmp_path / "sample.pdf"
    document = fitz.open()
    for index in range(1, 4):
        page = document.new_page()
        page.insert_text((72, 72), f"Page {index} has sample content.")
    document.save(path)
    document.close()
    return path


def test_pdf_loader_preserves_three_page_numbers(sample_pdf: Path) -> None:
    pages = load_pdf(sample_pdf)

    assert pages == [
        Page("Page 1 has sample content.", 1),
        Page("Page 2 has sample content.", 2),
        Page("Page 3 has sample content.", 3),
    ]


def test_pdf_loader_skips_blank_pages_but_keeps_source_number(tmp_path: Path) -> None:
    path = tmp_path / "with_blank.pdf"
    document = fitz.open()
    document.new_page()
    page = document.new_page()
    page.insert_text((72, 72), "Text on page two.")
    document.save(path)
    document.close()

    assert load_pdf(path) == [Page("Text on page two.", 2)]


def test_text_loader_cleans_wrapped_words_and_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("  A hyphen-\nated   word.\nNext line.  ", encoding="utf-8")

    assert load_text(path) == [Page("A hyphenated word. Next line.", 1)]


def test_markdown_loader_returns_single_page(tmp_path: Path) -> None:
    path = tmp_path / "sample.md"
    path.write_text("# Heading\n\nSome **bold** text.", encoding="utf-8")

    assert load_markdown(path) == [Page("# Heading\n\nSome **bold** text.", 1)]


@pytest.mark.parametrize("loader,suffix", [(load_text, ".txt"), (load_markdown, ".md")])
def test_text_loaders_reject_empty_files(tmp_path: Path, loader, suffix: str) -> None:
    path = tmp_path / f"empty{suffix}"
    path.write_text(" \n\t ", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        loader(path)


def test_pdf_loader_rejects_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"not a PDF")

    with pytest.raises(ValueError, match="Could not open PDF"):
        load_pdf(path)


def test_pdf_loader_ocr_fallback_preserves_page_number(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "scan.pdf"
    document = fitz.open()
    page = document.new_page()
    image = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 32, 32), 0)
    image.clear_with(255)
    page.insert_image(page.rect, stream=image.tobytes("png"))
    document.save(path)
    document.close()

    tessdata = tmp_path / "tessdata"

    def fake_ocr(_page, language, dpi, actual_tessdata):
        assert language == "eng"
        assert dpi == 300
        assert actual_tessdata == tessdata
        return "Text recognized from the scanned page."

    monkeypatch.setattr("documind.loaders.pdf._ocr_page", fake_ocr)

    assert load_pdf(path, ocr_tessdata=tessdata) == [
        Page("Text recognized from the scanned page.", 1)
    ]


def test_pdf_loader_reports_missing_tesseract_helpfully(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "scan.pdf"
    document = fitz.open()
    page = document.new_page()
    image = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 32, 32), 0)
    image.clear_with(255)
    page.insert_image(page.rect, stream=image.tobytes("png"))
    document.save(path)
    document.close()

    def missing_ocr(*_args, **_kwargs):
        raise RuntimeError("Tesseract language data is unavailable")

    monkeypatch.setattr("documind.loaders.pdf._ocr_page", missing_ocr)

    with pytest.raises(ValueError, match="Install Tesseract OCR"):
        load_pdf(path)


def test_pdf_loader_can_disable_ocr(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "scan.pdf"
    document = fitz.open()
    page = document.new_page()
    image = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 32, 32), 0)
    image.clear_with(255)
    page.insert_image(page.rect, stream=image.tobytes("png"))
    document.save(path)
    document.close()

    def unexpected_ocr(*_args, **_kwargs):
        raise AssertionError("OCR should be disabled")

    monkeypatch.setattr("documind.loaders.pdf._ocr_page", unexpected_ocr)

    with pytest.raises(ValueError, match="no extractable text"):
        load_pdf(path, ocr_enabled=False)

