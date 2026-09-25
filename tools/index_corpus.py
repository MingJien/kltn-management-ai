"""Index a typed local corpus into a disposable/local or Qdrant-service index.

Example: python -m tools.index_corpus --manifest data/manifests/synthetic-corpus.json --root data
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from qdrant_client import QdrantClient
from backend.ai.index import CorpusIndex, FastEmbedProvider
from backend.ai.manifest import CorpusSource
from backend.db.models.entities import RepositoryItem


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--local-path", type=Path)
    parser.add_argument("--persist-metadata", action="store_true", help="Write RepositoryItem metadata to PostgreSQL")
    args = parser.parse_args()
    sources = [CorpusSource.model_validate(item) for item in json.loads(
        args.manifest.read_text(encoding="utf-8-sig")
    )["sources"]]
    url = os.getenv("QDRANT_URL")
    if url:
        client = QdrantClient(url=url)
    elif args.local_path:
        args.local_path.mkdir(parents=True, exist_ok=True)
        client = QdrantClient(path=str(args.local_path))
    else:
        parser.error("Set QDRANT_URL or --local-path")
    index = CorpusIndex(client, FastEmbedProvider())
    db_engine = None
    if args.persist_metadata:
        from sqlalchemy import create_engine
        from backend.db.validate_schema import load_env
        load_env()
        if not os.getenv("DATABASE_URL"):
            parser.error("DATABASE_URL is required for --persist-metadata")
        db_engine = create_engine(os.environ["DATABASE_URL"])
    for source in sources:
        item_id = None
        if db_engine is not None:
            from sqlalchemy.orm import Session
            from backend.ai.ingestion import upsert_corpus_metadata, mark_index_state
            with Session(db_engine) as session, session.begin():
                item = upsert_corpus_metadata(session, source)
                mark_index_state(session, item, collection=index.collection,
                                 index_version=source.source_version,
                                 embedding_model=FastEmbedProvider.model_name, state="PENDING")
                item_id = item.id
        try:
            count = index.index_source(source, args.root)
            state = "REMOVED" if source.visibility == "REVOKED" else "INDEXED"
        except Exception:
            count = 0
            state = "FAILED"
            raise
        finally:
            if db_engine is not None and item_id is not None:
                with Session(db_engine) as session, session.begin():
                    item = session.get(RepositoryItem, item_id)
                    mark_index_state(session, item, collection=index.collection,
                                     index_version=source.source_version,
                                     embedding_model=FastEmbedProvider.model_name, state=state)
        print(source.source_id, source.source_type, count, "chunks")
    client.close()


if __name__ == "__main__":
    main()
