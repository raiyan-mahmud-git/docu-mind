"""Plain-text loader."""

from pathlib import Path

from documind.loaders.cleaning import clean_text
from documind.models import Page


def load_text(path: str | Path) -> list[Page]:
    """Load a UTF-8 text file as one cleaned page."""
    source = Path(path)
    try:
        raw_text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Could not read text file {source}: {exc}") from exc
    except UnicodeError as exc:
        raise ValueError(f"Text file {source} is not valid UTF-8") from exc

    text = clean_text(raw_text)
    if not text:
        raise ValueError(f"Text file {source} is empty")
    return [Page(text=text, page_number=1)]
