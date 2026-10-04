from __future__ import annotations

from dataclasses import asdict
from typing import Protocol
from backend.ai.index import CorpusIndex


class LLMProvider(Protocol):
    def answer(self, question: str, evidence: list[dict]) -> str: ...


def retrieve_answer(index: CorpusIndex, question: str, *, scope: str, provider: LLMProvider | None = None) -> dict:
    if provider is not None:
        # The advisor-approved external-data boundary is not implemented yet.
        # Never hand retrieved internal excerpts to an arbitrary provider.
        raise RuntimeError("Gemini is disabled until the published-source and question filters are implemented")
    hits = index.search(question, scope=scope, source_types={"REGULATION", "GUIDELINE", "FORM"}, representation="EVIDENCE")
    citations = [
        {key: value for key, value in asdict(hit).items() if key != "score"}
        for hit in hits
    ]
    if not hits:
        return {"status": "NO_EVIDENCE", "answer": None, "citations": []}
    return {"status": "RETRIEVAL_ONLY", "answer": None, "citations": citations}
