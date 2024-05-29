import json
import os
from typing import Any

from allotropy.allotrope.schema_parser.path_util import (
    get_schema_path_from_manifest,
    SCHEMA_DIR_PATH,
    SHARED_SCHEMAS_PATH,
)


def get_shared_definitions() -> dict[str, Any]:
    with open(os.path.join(SHARED_SCHEMAS_PATH, "definitions.json")) as f:
        return json.load(f)  # type: ignore[no-any-return]


def get_shared_unit_definitions() -> dict[str, Any]:
    with open(os.path.join(SHARED_SCHEMAS_PATH, "units.json")) as f:
        return json.load(f)  # type: ignore[no-any-return]


def add_definitions(schema: dict[str, Any]) -> dict[str, Any]:
    for file, section in [
        ("definitions", "defs"),
        ("units", "defs"),
        ("custom", "custom"),
    ]:
        existing = schema.get(f"${section}", {})
        with open(os.path.join(SHARED_SCHEMAS_PATH, f"{file}.json")) as f:
            additional = json.load(f)
        additional.update(existing)
        schema[f"${section}"] = additional
    return schema


def get_schema(schema_relative_path: str) -> dict[str, Any]:
    with open(os.path.join(SCHEMA_DIR_PATH, schema_relative_path)) as f:
        return add_definitions(json.load(f))


def get_schema_from_manifest(manifest: str) -> dict[str, Any]:
    return get_schema(get_schema_path_from_manifest(manifest))


def get_schema_from_model(model: Any) -> dict[str, Any]:
    manifest = getattr(model, "manifest", getattr(model, "field_asm_manifest", None))
    if not manifest:
        msg = f"No 'manifest' or 'field_asm_manifest' found in model: {type(model)}"
        raise ValueError(msg)
    return get_schema_from_manifest(manifest)
