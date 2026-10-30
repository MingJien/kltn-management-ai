"""Publish the FastAPI contract for the current application.

The output is JSON syntax, which is valid YAML 1.2. No database connection is
needed: FastAPI builds its OpenAPI document from registered routes and models.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.api.main import app

OUTPUT = Path(__file__).resolve().parents[1] / "docs/design/openapi.yaml"


def render() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the published file differs from FastAPI")
    args = parser.parse_args()
    current = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != current:
            parser.error("OpenAPI is out of date; run python -m tools.export_runtime_openapi")
        print("PASS published OpenAPI matches FastAPI")
        return
    OUTPUT.write_text(current, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
