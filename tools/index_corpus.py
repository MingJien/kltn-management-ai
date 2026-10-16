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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--local-path", type=Path)
    parser.add_argument("--persist-metadata", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.persist_metadata:
        parser.error("PostgreSQL corpus metadata is unavailable in the current 32-table schema")
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
    for source in sources:
        count = index.index_source(source, args.root)
        print(source.source_id, source.source_type, count, "chunks")
    client.close()


if __name__ == "__main__":
    main()
