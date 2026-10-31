"""Retrieval-grounded answer orchestration."""

from __future__ import annotations

from documind.llm.base import LLMProvider
from documind.llm.prompts import GROUNDED_SYSTEM_PROMPT, build_user_prompt
from documind.models import Answer
from documind.retrieval import Retriever

NO_DOCUMENT_ANSWER = "I can't find this in the documents."


class QAService:
    """Combine retrieval with an optional grounded language-model provider."""

    def __init__(self, retriever: Retriever, provider: LLMProvider | None = None) -> None:
        self.retriever = retriever
        self.provider = provider

    def ask(self, query: str, top_k: int = 5, use_llm: bool = False) -> Answer:
        """Answer from retrieved passages, refusing when retrieval finds no evidence."""
        sources = self.retriever.search(query, top_k)
        if not sources:
            return Answer(
                text=NO_DOCUMENT_ANSWER,
                sources=[],
                model_name=None,
                refused=True,
            )

        if not use_llm:
            return Answer(
                text=(
                    f"I found {len(sources)} relevant passage(s). "
                    "Enable LLM answers to synthesize them."
                ),
                sources=sources,
                model_name=None,
                refused=False,
            )
        if self.provider is None:
            raise RuntimeError(
                "LLM answers are disabled. Set DOCUMIND_LLM_PROVIDER to 'ollama' or 'anthropic'."
            )

        user_prompt = build_user_prompt(query, sources)
        answer_text = self.provider.generate(GROUNDED_SYSTEM_PROMPT, user_prompt).strip()
        if not answer_text:
            raise RuntimeError("The language model returned an empty answer")
        if answer_text.casefold() == NO_DOCUMENT_ANSWER.casefold():
            return Answer(answer_text, sources, self.provider.model_name, True)
        return Answer(answer_text, sources, self.provider.model_name, False)

    def close(self) -> None:
        """Close provider resources if a provider is configured."""
        if self.provider is not None:
            self.provider.close()


