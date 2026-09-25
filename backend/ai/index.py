from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from backend.ai.manifest import CorpusSource
from backend.ai.processing import representations

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION = "kltn_corpus_v1"


class EmbeddingProvider(Protocol):
    dimension: int
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedProvider:
    dimension = 384
    model_name = MODEL_NAME

    def __init__(self):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(model_name=self.model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.embed(texts)]


@dataclass(frozen=True)
class SearchHit:
    source_id: str
    source_type: str
    origin_type: str
    title: str
    score: float
    provenance: str
    source_ref: str | None
    source_url: str | None
    source_version: str
    representation: str
    excerpt: str


class CorpusIndex:
    """Qdrant is a derived index; the source manifest/PG metadata can rebuild it."""

    def __init__(self, client: QdrantClient, embedding: EmbeddingProvider, collection: str = COLLECTION):
        self.client = client
        self.embedding = embedding
        self.collection = collection

    def ensure_collection(self) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=self.embedding.dimension, distance=models.Distance.COSINE),
            )

    def index_source(self, source: CorpusSource, root: Path) -> int:
        if source.visibility == "REVOKED":
            self.delete_source(source.source_id)
            return 0
        parts = representations(source, root)
        if not parts:
            return 0
        vectors = self.embedding.embed_texts([content for _, content in parts])
        if len(vectors) != len(parts):
            raise ValueError("Embedding provider returned a different number of vectors")
        self.ensure_collection()
        points = []
        for position, ((kind, content), vector) in enumerate(zip(parts, vectors)):
            points.append(models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, f"{source.source_id}:{source.source_version}:{kind}:{position}")),
                vector=vector,
                payload={
                    "source_id": source.source_id, "source_type": source.source_type,
                    "origin_type": source.origin_type, "title": source.title,
                    "source_ref": source.source_ref, "source_url": source.source_url,
                    "source_version": source.source_version, "provenance": source.provenance,
                    "visibility": source.visibility, "allowed_scopes": source.allowed_scopes,
                    "representation": kind, "text": content,
                    "anonymized": source.anonymized, "evaluation_only": source.evaluation_only,
                },
            ))
        # Remove older chunks for this source so a changed version does not linger.
        self.delete_source(source.source_id)
        self.client.upsert(collection_name=self.collection, points=points, wait=True)
        return len(points)

    def delete_source(self, source_id: str) -> None:
        if not self.client.collection_exists(self.collection):
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(filter=models.Filter(must=[
                models.FieldCondition(key="source_id", match=models.MatchValue(value=source_id))
            ])),
            wait=True,
        )

    def search(
        self, query: str, *, scope: str, source_types: set[str] | None = None,
        representation: str | None = None, limit: int = 5,
    ) -> list[SearchHit]:
        if not query.strip() or not self.client.collection_exists(self.collection):
            return []
        filters = [
            models.FieldCondition(key="visibility", match=models.MatchAny(any=["PUBLISHED", "INTERNAL"] if scope == "INTERNAL" else ["PUBLISHED"])),
            models.FieldCondition(key="allowed_scopes", match=models.MatchValue(value=scope)),
        ]
        if source_types:
            filters.append(models.FieldCondition(key="source_type", match=models.MatchAny(any=sorted(source_types))))
        if representation:
            filters.append(models.FieldCondition(key="representation", match=models.MatchValue(value=representation)))
        vector = self.embedding.embed_texts([query])[0]
        result = self.client.query_points(
            collection_name=self.collection, query=vector,
            query_filter=models.Filter(must=filters), limit=limit, with_payload=True,
        ).points
        return [SearchHit(
            source_id=str(hit.payload["source_id"]), source_type=str(hit.payload["source_type"]),
            origin_type=str(hit.payload["origin_type"]), title=str(hit.payload["title"]),
            score=float(hit.score), provenance=str(hit.payload["provenance"]),
            source_ref=hit.payload.get("source_ref"), source_url=hit.payload.get("source_url"),
            source_version=str(hit.payload["source_version"]),
            representation=str(hit.payload["representation"]),
            excerpt=str(hit.payload["text"])[:500],
        ) for hit in result]
