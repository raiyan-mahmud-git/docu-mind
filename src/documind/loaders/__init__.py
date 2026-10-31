"""Document loaders for supported file formats."""

from documind.loaders.markdown import load_markdown
from documind.loaders.pdf import load_pdf
from documind.loaders.text import load_text

__all__ = ["load_markdown", "load_pdf", "load_text"]
