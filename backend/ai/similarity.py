from __future__ import annotations

from collections import Counter
import re
from backend.ai.index import CorpusIndex

WORD = re.compile(r"\w+", re.UNICODE)


def lexical_overlap(first: str, second: str) -> float:
    left, right = Counter(WORD.findall(first.casefold())), Counter(WORD.findall(second.casefold()))
    if not left:
        return 0.0
    return sum((left & right).values()) / sum(left.values())


def advisory_similarity(index: CorpusIndex, text: str, *, scope: str, limit: int = 5) -> dict:
    hits = index.search(text, scope=scope, source_types={
        "THESIS", "CAPSTONE_PROJECT", "TERM_PROJECT", "COURSE_PROJECT",
    }, representation="TOPIC", limit=limit)
    return {
        "status": "ADVISORY",
        "plagiarism_verdict": None,
        "upload_blocked": False,
        "metric_version": "lexical-overlap-v0-and-embedding-ranking-v0",
        "matches": [{
            "source_id": hit.source_id, "source_type": hit.source_type, "title": hit.title,
            "semantic_candidate_score": hit.score,
            "lexical_overlap": lexical_overlap(text, hit.excerpt),
            "provenance": hit.provenance, "source_ref": hit.source_ref,
        } for hit in hits],
    }
