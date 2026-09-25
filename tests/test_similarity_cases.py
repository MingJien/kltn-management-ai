"""Controlled functional similarity cases; not model-quality evaluation."""
from pathlib import Path

from qdrant_client import QdrantClient

from backend.ai.index import CorpusIndex
from backend.ai.manifest import CorpusSource
from backend.ai.similarity import advisory_similarity


class FixedEmbedding:
    dimension = 3

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]


def test_five_controlled_similarity_scenarios(tmp_path: Path):
    query = "Hệ thống quản lý khóa luận tốt nghiệp cho sinh viên"
    cases = {
        "exact_copy": query,
        "light_edit": "Hệ thống quản lý khóa luận tốt nghiệp dành sinh viên",
        "paraphrase": "Nền tảng theo dõi đồ án cuối khóa của người học",
        "same_topic_different_content": "Quản lý khóa luận bằng phân tích lịch bảo vệ của hội đồng",
        "unrelated": "Phân loại bệnh trên lá cây bằng ảnh chụp",
    }
    lexical = {}
    for label, title in cases.items():
        client = QdrantClient(":memory:")
        index = CorpusIndex(client, FixedEmbedding(), "controlled_similarity")
        source = CorpusSource(
            source_id=label, source_type="THESIS", origin_type="IMPORTED_DOCUMENT",
            title=title, source_ref=f"SYN-{label}", provenance="Synthetic controlled case",
            source_version="v1", visibility="PUBLISHED", allowed_scopes=["PUBLIC"],
            evaluation_only=True,
        )
        index.index_source(source, tmp_path)
        result = advisory_similarity(index, query, scope="PUBLIC")
        assert result["status"] == "ADVISORY"
        assert result["plagiarism_verdict"] is None
        assert result["upload_blocked"] is False
        assert result["matches"][0]["source_type"] == "THESIS"
        assert result["matches"][0]["provenance"] == "Synthetic controlled case"
        assert isinstance(result["matches"][0]["semantic_candidate_score"], float)
        lexical[label] = result["matches"][0]["lexical_overlap"]
        client.close()
    assert lexical["exact_copy"] == 1.0
    assert 0 < lexical["light_edit"] < 1.0
    assert lexical["paraphrase"] < lexical["light_edit"]
    assert lexical["same_topic_different_content"] > lexical["unrelated"]
    assert lexical["unrelated"] == 0.0
