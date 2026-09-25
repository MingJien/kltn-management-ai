import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.ai.ingestion import mark_index_state, upsert_corpus_metadata
from backend.ai.manifest import CorpusSource
from backend.db.models.entities import RepositoryItem, SearchIndexMetadata
from backend.db.validate_schema import load_env


def test_imported_corpus_metadata_is_not_a_fake_thesis():
    load_env()
    if not os.getenv("DATABASE_URL"):
        pytest.skip("PostgreSQL unavailable")
    engine = create_engine(os.environ["DATABASE_URL"])
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    source = CorpusSource(
        source_id="SYN-INGEST-UNIT", origin_type="IMPORTED_DOCUMENT",
        source_type="THESIS", title="Synthetic historic thesis",
        source_ref="SYN-INGEST-UNIT", source_url="https://example.invalid/source",
        provenance="Synthetic test", source_version="v1",
        visibility="INTERNAL", evaluation_only=True,
    )
    try:
        item = upsert_corpus_metadata(session, source)
        assert item.thesis_id is None
        assert item.published_document_version_id is None
        assert item.external_source_id == source.source_id
        mark_index_state(session, item, collection="synthetic", index_version="v1",
                         embedding_model="test-double", state="PENDING")
        session.flush()
        index_row = session.scalar(select(SearchIndexMetadata).where(
            SearchIndexMetadata.repository_item_id == item.id
        ))
        assert index_row.document_version_id is None
        assert index_row.state == "PENDING"
        revoked = source.model_copy(update={"visibility": "REVOKED", "source_version": "v2"})
        upsert_corpus_metadata(session, revoked)
        mark_index_state(session, item, collection="synthetic", index_version="v2",
                         embedding_model="test-double", state="REMOVED")
        session.flush()
        assert index_row.state == "REMOVED"
        assert {row.state for row in session.scalars(select(SearchIndexMetadata).where(
            SearchIndexMetadata.repository_item_id == item.id
        ))} == {"REMOVED"}
        assert session.scalar(select(RepositoryItem).where(
            RepositoryItem.external_source_id == source.source_id
        )).id == item.id
    finally:
        session.close()
        outer.rollback()
        connection.close()
        engine.dispose()
