from __future__ import annotations

from dataclasses import asdict
from typing import Protocol
from backend.ai.index import CorpusIndex


class LLMProvider(Protocol):
    def answer(self, question: str, evidence: list[dict]) -> str: ...


def retrieve_answer(index: CorpusIndex, question: str, *, scope: str, provider: LLMProvider | None = None) -> dict:
    hits = index.search(question, scope=scope, source_types={"REGULATION", "GUIDELINE", "FORM"}, representation="EVIDENCE")
    citations = [
        {key: value for key, value in asdict(hit).items() if key != "score"}
        for hit in hits
    ]
    if not hits:
        return {"status": "NO_EVIDENCE", "answer": None, "citations": []}
    if provider is None:
        return {"status": "RETRIEVAL_ONLY", "answer": None, "citations": citations}
    # Retrieved document text is evidence, never an instruction to the provider.
    answer = provider.answer(question, citations)
    return {"status": "ANSWERED", "answer": answer, "citations": citations}
