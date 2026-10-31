# DocuMind

DocuMind is a local-first document Q&A system. It will load PDFs, Markdown, and text files, retrieve relevant passages with citations, and optionally use an LLM to draft grounded answers.

## Development setup

Requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy
```

## Configuration

Settings use environment variables with defaults suitable for local development. Copy `.env.example` to `.env` to record local choices; secrets and `.env` are ignored by Git. The configuration module reads process environment variables directly.

## Loading, chunking, and vector search

Loaders support searchable text in PDF, Markdown, and UTF-8 plain-text files. Page numbers remain attached to every chunk. Chunking prefers paragraph and sentence boundaries, keeps words intact, and overlaps neighboring passages. Sentence-transformers loads lazily when embeddings are first requested. ChromaDB persists those vectors, while SQLite stores one record per document. Scanned PDFs without a text layer are not supported.

```powershell
uv run python -c "from pathlib import Path; from documind.embeddings import SentenceTransformerEmbedder; from documind.models import Chunk; from documind.vectorstore import ChromaVectorStore; s=ChromaVectorStore(Path('data/chroma')); c=Chunk('demo:0','demo','demo.txt',1,0,'A local vector search demo.'); e=SentenceTransformerEmbedder('all-MiniLM-L6-v2'); s.add([c],e.embed_texts([c.text])); print(s.query(e.embed_texts(['vector search'])[0],1))"
```

The first real embedding may download the configured model. Tests use a deterministic stand-in and do not download it.

## Project status

Phase 3: lazy embeddings, persistent vector storage, and a SQLite document registry. See the project brief for the staged roadmap.
