"""Markdown loader; Markdown is plain UTF-8 text at this stage."""

from pathlib import Path

from documind.loaders.text import load_text
from documind.models import Page


def load_markdown(path: str | Path) -> list[Page]:
    """Load a Markdown file as one cleaned page."""
    return load_text(path)
