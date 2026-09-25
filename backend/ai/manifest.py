"""A typed, synthetic-safe manifest for corpus ingestion.

Paths are local inputs, never public download URLs. Real source files stay outside Git.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, model_validator

SourceType = Literal[
    "THESIS", "CAPSTONE_PROJECT", "TERM_PROJECT", "COURSE_PROJECT",
    "REGULATION", "FORM", "GUIDELINE", "SYNTHETIC_TEST",
]
OriginType = Literal["MANAGED_THESIS", "IMPORTED_DOCUMENT", "OFFICIAL_SOURCE"]
Visibility = Literal["INTERNAL", "PUBLISHED", "REVOKED"]


class CorpusSource(BaseModel):
    source_id: str = Field(min_length=1)
    source_type: SourceType
    origin_type: OriginType
    title: str = Field(min_length=1)
    abstract: str | None = None
    keywords: list[str] = Field(default_factory=list)
    domain: str | None = None
    major: str | None = None
    source_ref: str | None = None
    source_url: str | None = None
    visibility: Visibility = "INTERNAL"
    local_file: Path | None = None
    anonymized: bool = False
    evaluation_only: bool = False
    provenance: str = Field(min_length=1)
    source_version: str = Field(min_length=1)
    allowed_scopes: list[str] = Field(default_factory=lambda: ["INTERNAL"])

    @model_validator(mode="after")
    def valid_origin(self):
        project_types = {"THESIS", "CAPSTONE_PROJECT", "TERM_PROJECT", "COURSE_PROJECT", "SYNTHETIC_TEST"}
        official_types = {"REGULATION", "FORM", "GUIDELINE"}
        if self.origin_type == "MANAGED_THESIS":
            raise ValueError("Managed theses are ingested from PostgreSQL, not an external manifest")
        if self.origin_type == "IMPORTED_DOCUMENT" and self.source_type not in project_types:
            raise ValueError("Imported document type conflicts with origin")
        if self.origin_type == "OFFICIAL_SOURCE" and self.source_type not in official_types:
            raise ValueError("Official source type conflicts with origin")
        if not (self.source_ref or self.source_url or self.local_file):
            raise ValueError("A verifiable source reference or local file is required")
        if self.source_url is not None and not self.source_url.startswith("https://"):
            raise ValueError("Public source URL must use HTTPS")
        if not self.allowed_scopes:
            raise ValueError("At least one authorized scope is required")
        return self
