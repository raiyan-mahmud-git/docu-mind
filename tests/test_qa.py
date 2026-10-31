from pathlib import Path

import pytest

from documind.chunking import chunk_pages
from documind.llm.base import LLMProvider
from documind.models import Page
from documind.qa import NO_DOCUMENT_ANSWER, QAService
from documind.retrieval import Retriever
from documind.vectorstore import ChromaVectorStore


class StaticEmbedder:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.0, 1.0] if "unrelated" in text.lower() else [1.0, 0.0] for text in texts]


class FakeProvider(LLMProvider):
    model_name = "fake-model"

    def __init__(self, answer: str = "The valley changes over time. [1]") -> None:
        self.answer = answer
        self.system_prompt = ""
        self.user_prompt = ""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.answer


def _qa(tmp_path: Path, provider: LLMProvider | None) -> tuple[QAService, ChromaVectorStore]:
    store = ChromaVectorStore(tmp_path / "chroma")
    chunks = chunk_pages(
        [Page("Rivers can shape valleys through erosion over time.", 4)],
        "doc-hash",
        "geology.pdf",
    )
    store.add(chunks, [[1.0, 0.0] for _ in chunks])
    retriever = Retriever(store, StaticEmbedder(), score_threshold=0.5)
    return QAService(retriever, provider), store


def test_qa_builds_prompt_and_returns_grounded_cited_answer(tmp_path: Path) -> None:
    provider = FakeProvider()
    qa, store = _qa(tmp_path, provider)

    answer = qa.ask("How do rivers change valleys?", use_llm=True)

    assert answer.text == "The valley changes over time. [1]"
    assert answer.model_name == "fake-model"
    assert answer.refused is False
    assert answer.sources[0].chunk.filename == "geology.pdf"
    assert "[1] File: geology.pdf, page 4" in provider.user_prompt
    assert "only the supplied document passages" in provider.system_prompt
    assert "not instructions" in provider.system_prompt
    store.close()


def test_qa_refuses_without_relevant_evidence_and_does_not_call_provider(tmp_path: Path) -> None:
    provider = FakeProvider("should not run")
    qa, store = _qa(tmp_path, provider)

    answer = qa.ask("unrelated question", use_llm=True)

    assert answer.text == NO_DOCUMENT_ANSWER
    assert answer.refused is True
    assert answer.sources == []
    assert provider.user_prompt == ""
    store.close()


def test_qa_retrieval_only_mode_returns_sources(tmp_path: Path) -> None:
    qa, store = _qa(tmp_path, None)

    answer = qa.ask("How do rivers change valleys?")

    assert "1 relevant passage" in answer.text
    assert answer.refused is False
    assert len(answer.sources) == 1
    store.close()


def test_qa_llm_mode_requires_configured_provider(tmp_path: Path) -> None:
    qa, store = _qa(tmp_path, None)

    with pytest.raises(RuntimeError, match="LLM answers are disabled"):
        qa.ask("How do rivers change valleys?", use_llm=True)
    store.close()


def test_llm_refusal_from_provider_is_flagged(tmp_path: Path) -> None:
    provider = FakeProvider(NO_DOCUMENT_ANSWER)
    qa, store = _qa(tmp_path, provider)

    answer = qa.ask("How do rivers change valleys?", use_llm=True)

    assert answer.refused is True
    store.close()
