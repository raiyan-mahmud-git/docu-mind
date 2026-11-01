"""Document loaders for supported file formats."""

from documind.loaders.image import load_image
from documind.loaders.markdown import load_markdown
from documind.loaders.pdf import load_pdf
from documind.loaders.text import load_text

__all__ = ["load_image", "load_markdown", "load_pdf", "load_text"]
