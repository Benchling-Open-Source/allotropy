from collections.abc import Mapping
import copy
import json
from pathlib import Path
from typing import Any

import jsonschema

from allotropy.allotrope.schema_parser.path_util import (
    get_full_schema_path,
    get_schema_path_from_asm,
    get_schema_path_from_manifest,
    SCHEMA_V2_DIR_PATH,
    SHARED_SCHEMAS_DEFINITIONS_PATH,
)
from allotropy.exceptions import AllotropeSerializationError, AllotropeValidationError

DEFAULT_ENCODING = "UTF-8"

# Override format checker to remove "uri-reference" check, which ASM schemas fail against.
FORMAT_CHECKER = copy.deepcopy(
    jsonschema.validators.Draft202012Validator.FORMAT_CHECKER
)
FORMAT_CHECKER.checkers.pop("uri-reference", None)


def get_shared_definitions() -> dict[str, Any]:
    with open(
        Path(SHARED_SCHEMAS_DEFINITIONS_PATH, "definitions.json"),
        encoding=DEFAULT_ENCODING,
    ) as f:
        return json.load(f)  # type: ignore[no-any-return]


def get_shared_unit_definitions() -> dict[str, Any]:
    with open(
        Path(SHARED_SCHEMAS_DEFINITIONS_PATH, "units.json"), encoding=DEFAULT_ENCODING
    ) as f:
        return json.load(f)  # type: ignore[no-any-return]


def add_definitions(schema: dict[str, Any]) -> dict[str, Any]:
    for file, section in [
        ("definitions", "defs"),
        ("units", "defs"),
        ("custom", "custom"),
    ]:
        existing = schema.get(f"${section}", {})
        with open(
            Path(SHARED_SCHEMAS_DEFINITIONS_PATH, f"{file}.json"),
            encoding=DEFAULT_ENCODING,
        ) as f:
            additional = json.load(f)
        additional.update(existing)
        schema[f"${section}"] = additional
    return schema


def get_schema(schema_path: Path) -> dict[str, Any]:
    with open(get_full_schema_path(schema_path), encoding=DEFAULT_ENCODING) as f:
        return add_definitions(json.load(f))


def get_schema_from_manifest(manifest: str) -> dict[str, Any]:
    return get_schema(get_schema_path_from_manifest(manifest))


def get_schema_from_asm(asm_dict: Mapping[str, Any]) -> dict[str, Any]:
    return get_schema(get_schema_path_from_asm(asm_dict))


def get_schema_from_model(model: Any) -> dict[str, Any]:
    manifest = getattr(model, "manifest", getattr(model, "field_asm_manifest", None))
    if not manifest:
        msg = f"No 'manifest' or 'field_asm_manifest' found in model: {type(model)}"
        raise ValueError(msg)
    return get_schema_from_manifest(manifest)


def validate_asm_schema(asm_dict: dict[str, Any]) -> None:
    try:
        allotrope_schema = get_schema_from_asm(asm_dict)
    except Exception as e:
        msg = f"Failed to retrieve schema for model: {e}"
        raise AllotropeSerializationError(msg) from e

    try:
        jsonschema.validators.Draft202012Validator.check_schema(
            allotrope_schema, format_checker=FORMAT_CHECKER
        )
        validator = jsonschema.validators.Draft202012Validator(allotrope_schema)
        validator.validate(asm_dict)
    except Exception as e:
        msg = f"Failed to validate allotrope model against schema: {e}"
        raise AllotropeValidationError(msg) from e


# ---------------------------------------------------------------------------
# V2 schema validation (uses RefResolver with pre-loaded schema store)
# ---------------------------------------------------------------------------

# Cached store of all V2 schemas keyed by $id URI, loaded lazily on first use.
_v2_schema_store: dict[str, dict[str, Any]] | None = None


def _get_v2_schema_store() -> dict[str, dict[str, Any]]:
    """Load all V2 schemas into a dict keyed by their $id URI."""
    global _v2_schema_store  # noqa: PLW0603
    if _v2_schema_store is not None:
        return _v2_schema_store

    store: dict[str, dict[str, Any]] = {}
    for schema_file in SCHEMA_V2_DIR_PATH.rglob("*.schema.json"):
        with open(schema_file, encoding=DEFAULT_ENCODING) as f:
            schema = json.load(f)
        schema_id = schema.get("$id")
        if schema_id:
            store[schema_id] = schema
    _v2_schema_store = store
    return store


def _get_v2_schema(schema_path: Path) -> dict[str, Any]:
    """Load a V2 schema from the schemas_v2/ directory."""
    full_path = SCHEMA_V2_DIR_PATH / schema_path
    with open(full_path, encoding=DEFAULT_ENCODING) as f:
        return json.load(f)  # type: ignore[no-any-return]


def validate_v2_asm_schema(asm_dict: dict[str, Any]) -> None:
    """Validate an ASM dict against V2 schemas with cross-schema $ref resolution."""
    try:
        schema_path = get_schema_path_from_asm(asm_dict)
        schema = _get_v2_schema(schema_path)
    except Exception as e:
        msg = f"Failed to retrieve V2 schema for model: {e}"
        raise AllotropeSerializationError(msg) from e

    try:
        store = _get_v2_schema_store()
        resolver = jsonschema.RefResolver(
            base_uri=schema.get("$id", ""),
            referrer=schema,
            store=store,  # type: ignore[arg-type]
        )
        validator = jsonschema.validators.Draft202012Validator(
            schema, resolver=resolver, format_checker=FORMAT_CHECKER
        )
        validator.validate(asm_dict)
    except Exception as e:
        msg = f"Failed to validate allotrope model against V2 schema: {e}"
        raise AllotropeValidationError(msg) from e
