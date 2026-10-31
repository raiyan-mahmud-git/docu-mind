"""SQLite document registry, separate from passage vectors."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from documind.models import Document


class DocumentRegistry:
    """Persist one metadata row per ingested document."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    sha256 TEXT NOT NULL UNIQUE,
                    pages INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Document:
        return Document(
            id=row["id"],
            filename=row["filename"],
            sha256=row["sha256"],
            pages=row["pages"],
            chunk_count=row["chunk_count"],
            created_at=row["created_at"],
        )

    def register(
        self, doc_id: str, filename: str, sha256: str, pages: int, chunk_count: int
    ) -> Document:
        """Insert or refresh a document row, preserving its original creation time."""
        if pages < 0 or chunk_count < 0:
            raise ValueError("pages and chunk_count must be non-negative")
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO documents (id, filename, sha256, pages, chunk_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    filename = excluded.filename,
                    sha256 = excluded.sha256,
                    pages = excluded.pages,
                    chunk_count = excluded.chunk_count
                """,
                (doc_id, filename, sha256, pages, chunk_count, created_at),
            )
        document = self.get(doc_id)
        if document is None:
            raise RuntimeError(f"Document registry failed to save {doc_id}")
        return document

    def get(self, doc_id: str) -> Document | None:
        """Return a document by its ID, or None if it is not registered."""
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return self._from_row(row) if row is not None else None

    def list_documents(self) -> list[Document]:
        """List registered documents, newest first."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM documents ORDER BY created_at DESC, filename ASC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def delete(self, doc_id: str) -> bool:
        """Delete a document record and report whether it existed."""
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        return cursor.rowcount > 0
