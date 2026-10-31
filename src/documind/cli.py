"""Typer CLI for local document ingestion and search."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from documind.config import Settings
from documind.db import DocumentRegistry
from documind.embeddings import get_embedder
from documind.ingest import IngestionPipeline, delete_document
from documind.models import Document, SearchResult
from documind.retrieval import Retriever
from documind.vectorstore import ChromaVectorStore

app = typer.Typer(no_args_is_help=True, help="Index local documents and search their passages.")


@dataclass
class Runtime:
    """Resources shared by one CLI command."""

    registry: DocumentRegistry
    vector_store: ChromaVectorStore
    ingestor: IngestionPipeline
    retriever: Retriever

    def close(self) -> None:
        self.vector_store.close()


def _make_runtime() -> Runtime:
    settings = Settings.from_env()
    registry = DocumentRegistry(settings.sqlite_path)
    vector_store = ChromaVectorStore(settings.chroma_dir)
    embedder = get_embedder(settings.embedding_model)
    return Runtime(
        registry=registry,
        vector_store=vector_store,
        ingestor=IngestionPipeline(
            registry,
            vector_store,
            embedder,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        ),
        retriever=Retriever(vector_store, embedder, settings.score_threshold),
    )


def _document_line(document: Document) -> str:
    return (
        f"{document.id}  {document.filename}  "
        f"{document.pages} pages  {document.chunk_count} chunks"
    )


def _result_lines(results: list[SearchResult]) -> list[str]:
    lines: list[str] = []
    for result in results:
        snippet = " ".join(result.chunk.text.split())
        if len(snippet) > 300:
            snippet = snippet[:297].rstrip() + "..."
        lines.append(
            f"[{result.rank}] score={result.score:.3f}  "
            f"{result.chunk.filename}, page {result.chunk.page_number}\n{snippet}"
        )
    return lines


def _fail(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


@app.command()
def ingest(
    path: Annotated[Path, typer.Argument(help="PDF, Markdown, or text file to index")],
) -> None:
    """Index a local document file."""
    try:
        runtime = _make_runtime()
    except Exception as exc:
        _fail(str(exc))
    try:
        document = runtime.ingestor.ingest_file(path)
        typer.echo(f"Indexed {document.filename}: {document.pages} pages, "
                   f"{document.chunk_count} chunks\nID: {document.id}")
    except (OSError, ValueError, RuntimeError) as exc:
        _fail(str(exc))
    finally:
        runtime.close()


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Question or phrase to search for")],
    top_k: Annotated[int | None, typer.Option(min=1, help="Maximum results to show")] = None,
) -> None:
    """Search indexed documents and print passage citations."""
    try:
        runtime = _make_runtime()
    except Exception as exc:
        _fail(str(exc))
    try:
        settings = Settings.from_env()
        results = runtime.retriever.search(query, top_k or settings.top_k)
        if not results:
            typer.echo("No relevant passage found.")
            return
        typer.echo("\n\n".join(_result_lines(results)))
    except (ValueError, RuntimeError) as exc:
        _fail(str(exc))
    finally:
        runtime.close()


@app.command("list")
def list_documents() -> None:
    """List indexed documents."""
    try:
        runtime = _make_runtime()
    except Exception as exc:
        _fail(str(exc))
    try:
        documents = runtime.registry.list_documents()
        if not documents:
            typer.echo("No documents indexed.")
            return
        for document in documents:
            typer.echo(_document_line(document))
    finally:
        runtime.close()


@app.command()
def delete(
    doc_id: Annotated[str, typer.Argument(help="Document ID shown by the list command")],
) -> None:
    """Delete a document and all of its stored chunks."""
    try:
        runtime = _make_runtime()
    except Exception as exc:
        _fail(str(exc))
    try:
        if delete_document(doc_id, runtime.registry, runtime.vector_store):
            typer.echo(f"Deleted document {doc_id}.")
        else:
            typer.echo(f"Document {doc_id} was not found.")
    finally:
        runtime.close()


def main() -> None:
    """Run the CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app()

