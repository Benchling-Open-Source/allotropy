import json
import os
from pathlib import Path
from typing import Any

SCHEMAS_DIR = os.path.join(Path(__file__).parent, "schemas")


def add_definitions(schema: dict[str, Any]) -> dict[str, Any]:
    for file, section in [
        ("definitions", "defs"),
        ("units", "defs"),
        ("custom", "custom"),
    ]:
        existing = schema.get(f"${section}", {})
        with open(
            os.path.join(SCHEMAS_DIR, "shared", "definitions", f"{file}.json")
        ) as f:
            additional = json.load(f)
        additional.update(existing)
        schema[f"${section}"] = additional
    return schema


def get_schema(schema_relative_path: str) -> dict[str, Any]:
    with open(os.path.join(SCHEMAS_DIR, schema_relative_path)) as f:
        return add_definitions(json.load(f))
