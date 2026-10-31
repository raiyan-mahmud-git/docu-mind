from pathlib import Path

import pytest

from documind.db import DocumentRegistry
from documind.models import Document


def test_registry_register_get_list_and_delete(tmp_path: Path) -> None:
    registry = DocumentRegistry(tmp_path / "data" / "registry.sqlite3")

    document = registry.register("hash-1", "notes.md", "hash-1", 2, 4)

    assert document == Document("hash-1", "notes.md", "hash-1", 2, 4, document.created_at)
    assert registry.get("hash-1") == document
    assert registry.list_documents() == [document]
    assert registry.delete("hash-1") is True
    assert registry.delete("hash-1") is False
    assert registry.get("hash-1") is None


def test_registry_reingest_updates_without_duplicate(tmp_path: Path) -> None:
    registry = DocumentRegistry(tmp_path / "registry.sqlite3")
    first = registry.register("hash-1", "old.txt", "hash-1", 1, 2)

    updated = registry.register("hash-1", "renamed.txt", "hash-1", 3, 5)

    assert updated.filename == "renamed.txt"
    assert updated.pages == 3
    assert updated.chunk_count == 5
    assert updated.created_at == first.created_at
    assert len(registry.list_documents()) == 1


def test_registry_validates_counts(tmp_path: Path) -> None:
    registry = DocumentRegistry(tmp_path / "registry.sqlite3")

    with pytest.raises(ValueError, match="non-negative"):
        registry.register("hash-1", "file.txt", "hash-1", -1, 0)
