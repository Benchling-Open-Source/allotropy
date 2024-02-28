import json
import os
from pathlib import Path
import re
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


def get_schema_path_from_manifest(manifest: str) -> str:
    match = re.match(r"http://purl.allotrope.org/manifests/(.*)\.manifest", manifest)
    if not match:
        msg = f"No matching schema in repo for manifest: {manifest}"
        raise ValueError(msg)
    return f"{match.groups()[0]}.json"


def get_schema_from_manifest(manifest: str) -> dict[str, Any]:
    return get_schema(get_schema_path_from_manifest(manifest))


def get_schema_from_model(model: Any) -> dict[str, Any]:
    manifest = getattr(model, "manifest", getattr(model, "field_asm_manifest", None))
    if not manifest:
        msg = f"No 'manifest' or 'field_asm_manifest' found in model: {type(model)}"
        raise ValueError(msg)
    return get_schema_from_manifest(manifest)
