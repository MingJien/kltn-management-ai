"""Keep the submitted API contract synchronized with the running routes."""
import json
from pathlib import Path

from backend.api.main import app


def test_published_openapi_matches_fastapi() -> None:
    path = Path(__file__).resolve().parents[1] / "docs/design/openapi.yaml"
    assert json.loads(path.read_text(encoding="utf-8")) == app.openapi()
