import pytest

from documind.chunking import chunk_pages
from documind.models import Chunk, Page


def test_chunks_respect_size_and_keep_words_intact() -> None:
    text = " ".join(["alpha", "beta", "gamma", "delta", "epsilon"] * 5)

    chunks = chunk_pages([Page(text, 1)], "abc123", "notes.txt", chunk_size=24, overlap=5)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 24 for chunk in chunks)
    assert set(" ".join(chunk.text for chunk in chunks).split()) == set(text.split())


def test_overlap_repeats_context_between_chunks() -> None:
    pages = [Page("one two three four five six seven eight nine ten", 1)]

    chunks = chunk_pages(pages, "hash", "source.txt", chunk_size=15, overlap=5)

    assert len(chunks) > 1
    assert any(
        set(left.text.split()) & set(right.text.split())
        for left, right in zip(chunks, chunks[1:], strict=False)
    )


def test_page_number_and_deterministic_ids_are_preserved() -> None:
    pages = [Page("First page has some text.", 2), Page("Second page also has text.", 7)]

    first = chunk_pages(pages, "f00d", "book.pdf", chunk_size=18, overlap=3)
    second = chunk_pages(pages, "f00d", "book.pdf", chunk_size=18, overlap=3)

    assert first == second
    assert [chunk.id for chunk in first] == [f"f00d:{i}" for i in range(len(first))]
    assert [chunk.page_number for chunk in first] == [2, 2, 7, 7]
    assert all(chunk.doc_id == "f00d" and chunk.filename == "book.pdf" for chunk in first)


def test_empty_page_produces_no_chunks() -> None:
    assert chunk_pages([Page("  ", 3)], "hash", "empty.txt") == []


@pytest.mark.parametrize("chunk_size,overlap", [(0, 0), (10, -1), (10, 10)])
def test_invalid_chunk_configuration_is_rejected(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_pages([Page("text", 1)], "hash", "doc.txt", chunk_size, overlap)


def test_chunk_model_has_expected_values() -> None:
    chunk = Chunk("id", "doc", "file.md", 1, 0, "content")
    assert chunk.text == "content"

