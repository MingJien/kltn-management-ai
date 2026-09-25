from __future__ import annotations

import re
from pathlib import Path
from docx import Document
from pypdf import PdfReader

from backend.ai.manifest import CorpusSource


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        doc = Document(path)
        return "\n".join(
            [p.text for p in doc.paragraphs]
            + [" | ".join(cell.text for cell in row.cells) for table in doc.tables for row in table.rows]
        )
    if suffix == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    raise ValueError("Only UTF-8 text, Markdown, DOCX and text-layer PDF are supported")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def topic_representation(source: CorpusSource) -> str:
    """Use topic metadata; avoid unrelated report boilerplate for similar-topic ranking."""
    return normalize(" ".join(
        item for item in (source.title, source.abstract or "", " ".join(source.keywords),
                         source.domain or "", source.major or "") if item
    ))


def chunk_text(text: str, *, size: int = 900, overlap: int = 120) -> list[str]:
    text = normalize(text)
    if not text:
        return []
    if size <= overlap or overlap < 0:
        raise ValueError("size must exceed overlap")
    chunks = []
    cursor = 0
    while cursor < len(text):
        end = min(cursor + size, len(text))
        if end < len(text):
            split = text.rfind(" ", cursor + size // 2, end)
            if split > cursor:
                end = split
        chunks.append(text[cursor:end])
        if end == len(text):
            break
        cursor = max(cursor + 1, end - overlap)
    return chunks


def representations(source: CorpusSource, root: Path) -> list[tuple[str, str]]:
    result = [("TOPIC", topic_representation(source))]
    if source.local_file:
        path = (root / source.local_file).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Corpus path must stay under the configured root")
        if not path.is_file():
            raise FileNotFoundError(path)
        content = extract_text(path)
        result.extend(("EVIDENCE", part) for part in chunk_text(content))
    return [(kind, text) for kind, text in result if text]
