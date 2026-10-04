from pathlib import Path

import pytest
from qdrant_client import QdrantClient
from pydantic import ValidationError

from backend.ai.index import CorpusIndex
from backend.ai.manifest import CorpusSource
from backend.ai.processing import chunk_text, topic_representation
from backend.ai.rag import retrieve_answer
from backend.ai.similarity import advisory_similarity, lexical_overlap


class TestVectorProvider:
    """Deterministic test double, never evidence of model quality."""
    dimension = 3

    def embed_texts(self, texts):
        import numpy as np
        vectors = []
        for text in texts:
            low = text.casefold()
            vector = np.array([
                1.0 if "đăng ký" in low or "nhóm" in low else 0.1,
                1.0 if "hướng dẫn" in low or "nộp" in low else 0.1,
                1.0 if "điểm" in low else 0.1,
            ])
            vectors.append((vector / np.linalg.norm(vector)).tolist())
        return vectors


def source(source_id, source_type, origin, visibility, scopes, **extra):
    return CorpusSource(
        source_id=source_id, source_type=source_type, origin_type=origin,
        title=extra.pop("title", source_id), source_ref=source_id,
        visibility=visibility, provenance="Synthetic test only",
        source_version="v1", allowed_scopes=scopes, evaluation_only=True, **extra,
    )


def test_manifest_and_text():
    with pytest.raises(ValidationError):
        source("bad", "THESIS", "OFFICIAL_SOURCE", "PUBLISHED", ["PUBLIC"])
    assert "tiến độ" in topic_representation(source(
        "t", "THESIS", "IMPORTED_DOCUMENT", "PUBLISHED", ["PUBLIC"],
        title="Quản lý tiến độ", abstract="Sinh viên",
    ))
    assert len(chunk_text("nội dung " * 250)) > 1


def test_qdrant_scoped_retrieval_and_rag(tmp_path):
    (tmp_path / "guide.txt").write_text("Hướng dẫn giả lập nộp hồ sơ thử nghiệm.", encoding="utf-8")
    client = QdrantClient(":memory:")
    index = CorpusIndex(client, TestVectorProvider(), "test_corpus")
    public = source(
        "guide-public", "GUIDELINE", "OFFICIAL_SOURCE", "PUBLISHED", ["PUBLIC", "INTERNAL"],
        title="Hướng dẫn GIẢ LẬP", local_file=Path("guide.txt"),
    )
    private = source(
        "guide-private", "GUIDELINE", "OFFICIAL_SOURCE", "INTERNAL", ["INTERNAL"],
        title="Hướng dẫn nội bộ GIẢ LẬP", local_file=Path("guide.txt"),
    )
    thesis = source(
        "thesis", "THESIS", "IMPORTED_DOCUMENT", "PUBLISHED", ["PUBLIC", "INTERNAL"],
        title="Đăng ký nhóm sinh viên", abstract="Đăng ký đề tài",
    )
    assert index.index_source(public, tmp_path) == 2
    index.index_source(private, tmp_path)
    index.index_source(thesis, tmp_path)
    hits = index.search("hướng dẫn nộp", scope="PUBLIC", source_types={"GUIDELINE"}, representation="EVIDENCE")
    assert [hit.source_id for hit in hits] == ["guide-public"]
    assert hits[0].source_type == "GUIDELINE"
    assert hits[0].provenance == "Synthetic test only"
    assert len(index.search("hướng dẫn nộp", scope="INTERNAL", source_types={"GUIDELINE"}, representation="EVIDENCE")) == 2
    rag = retrieve_answer(index, "Nộp hồ sơ thế nào?", scope="PUBLIC")
    assert rag["status"] == "RETRIEVAL_ONLY"
    assert rag["answer"] is None
    assert rag["citations"][0]["source_id"] == "guide-public"
    class ForbiddenProvider:
        def answer(self, question, evidence):
            raise AssertionError("External provider must never receive content")

    try:
        retrieve_answer(index, "Nộp hồ sơ thế nào?", scope="INTERNAL", provider=ForbiddenProvider())
    except RuntimeError as exc:
        assert "disabled" in str(exc)
    else:
        raise AssertionError("External provider was not blocked")
    assert retrieve_answer(index, "?", scope="OTHER")["status"] == "NO_EVIDENCE"
    similarities = advisory_similarity(index, "Đăng ký nhóm", scope="PUBLIC")
    assert similarities["status"] == "ADVISORY"
    assert similarities["upload_blocked"] is False
    assert similarities["plagiarism_verdict"] is None
    assert similarities["matches"][0]["source_type"] == "THESIS"
    assert lexical_overlap("đăng ký nhóm", "đăng ký nhóm") == 1.0
    assert lexical_overlap("đăng ký nhóm", "điểm hội đồng") == 0.0
    revoked = public.model_copy(update={"visibility": "REVOKED", "source_version": "v2"})
    assert index.index_source(revoked, tmp_path) == 0
    assert index.search("hướng dẫn nộp", scope="PUBLIC", source_types={"GUIDELINE"}) == []
    index.index_source(public, tmp_path)
    assert index.search("hướng dẫn nộp", scope="PUBLIC", source_types={"GUIDELINE"})
    client.close()
