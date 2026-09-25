from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.ai.manifest import CorpusSource
from backend.db.models.entities import RepositoryItem, SearchIndexMetadata


def upsert_corpus_metadata(session: Session, source: CorpusSource) -> RepositoryItem:
    """Persist the allowed external-source identity before building a Qdrant index."""
    if source.origin_type == "MANAGED_THESIS":
        raise ValueError("Managed theses use the publication workflow")
    row = session.scalar(select(RepositoryItem).where(
        RepositoryItem.external_source_id == source.source_id
    ).with_for_update())
    if row is None:
        row = RepositoryItem(external_source_id=source.source_id)
        session.add(row)
    row.origin_type = source.origin_type
    row.source_type = source.source_type
    row.title = source.title
    row.abstract = source.abstract
    row.keywords = source.keywords
    row.source_ref = source.source_ref or source.source_id
    row.source_url = source.source_url
    row.provenance = source.provenance
    row.source_version = source.source_version
    row.visibility = source.visibility
    session.flush()
    return row


def mark_index_state(
    session: Session, item: RepositoryItem, *,
    collection: str, index_version: str, embedding_model: str, state: str,
) -> None:
    if state == "REMOVED":
        for previous in session.scalars(select(SearchIndexMetadata).where(
            SearchIndexMetadata.repository_item_id == item.id,
            SearchIndexMetadata.index_name == collection,
        ).with_for_update()):
            previous.state = "REMOVED"
    row = session.scalar(select(SearchIndexMetadata).where(
        SearchIndexMetadata.repository_item_id == item.id,
        SearchIndexMetadata.index_name == collection,
        SearchIndexMetadata.index_version == index_version,
    ).with_for_update())
    if row is None:
        row = SearchIndexMetadata(repository_item_id=item.id, index_name=collection,
                                  index_version=index_version)
        session.add(row)
    row.document_version_id = None
    row.embedding_model = embedding_model
    row.chunking_version = "topic-v1-evidence-900-120"
    row.external_point_namespace = item.external_source_id
    row.state = state
    session.flush()
