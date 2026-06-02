from collections.abc import Mapping
import copy
import json
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from allotropy.allotrope.path_util import (
    get_full_schema_path,
    get_schema_path_from_asm,
    get_schema_path_from_manifest,
    SCHEMA_DIR_PATH,
)
from allotropy.exceptions import AllotropeSerializationError, AllotropeValidationError

DEFAULT_ENCODING = "UTF-8"

# Override format checker to remove "uri-reference" check, which ASM schemas fail against.
FORMAT_CHECKER = copy.deepcopy(
    jsonschema.validators.Draft202012Validator.FORMAT_CHECKER
)
FORMAT_CHECKER.checkers.pop("uri-reference", None)


# ---------------------------------------------------------------------------
# Optimized array items validator
# ---------------------------------------------------------------------------
# Data cube arrays can contain millions of floats. The default jsonschema
# items validator calls validator.descend() per element — extremely slow for
# simple type-only schemas like {"type": "number"} or
# {"anyOf": [{"type": "number"}, {"type": "null"}]}.
# We detect these patterns and do a single bulk isinstance pass instead.

_SIMPLE_TYPE_MAP: dict[str, tuple[tuple[type, ...], bool]] = {
    "number": ((int, float), True),
    "string": ((str,), False),
    "boolean": ((bool,), False),
    "integer": ((int,), True),
    "null": ((type(None),), False),
}


def _extract_accepted_types(
    items_schema: Any,
) -> tuple[tuple[type, ...], bool] | None:
    """If items_schema is a simple type-only check, return (accepted_types, exclude_bool)."""
    if not isinstance(items_schema, dict):
        return None

    keys = set(items_schema.keys())

    if keys == {"type"} and isinstance(items_schema["type"], str):
        return _SIMPLE_TYPE_MAP.get(items_schema["type"])

    if keys == {"anyOf"} and isinstance(items_schema["anyOf"], list):
        combined: set[type] = set()
        exclude_bool = False
        for sub in items_schema["anyOf"]:
            if not (
                isinstance(sub, dict)
                and set(sub.keys()) == {"type"}
                and isinstance(sub["type"], str)
            ):
                return None
            entry = _SIMPLE_TYPE_MAP.get(sub["type"])
            if entry is None:
                return None
            combined.update(entry[0])
            exclude_bool = exclude_bool or entry[1]
        return (tuple(combined), exclude_bool)

    return None


_original_items = jsonschema.validators.Draft202012Validator.VALIDATORS["items"]


def _fast_items_validator(
    validator: Any, items_schema: Any, instance: Any, schema: Any
) -> Any:
    """items validator that bulk-checks homogeneous primitive arrays."""
    if not validator.is_type(instance, "array"):
        return

    if schema.get("prefixItems") or not instance:
        yield from _original_items(validator, items_schema, instance, schema)
        return

    if items_schema is False:
        yield ValidationError(f"Expected at most 0 items, but found {len(instance)}")
        return

    type_info = _extract_accepted_types(items_schema)
    if type_info is None:
        yield from _original_items(validator, items_schema, instance, schema)
        return

    accepted_types, exclude_bool = type_info
    if exclude_bool:
        for i, v in enumerate(instance):
            if isinstance(v, bool) or not isinstance(v, accepted_types):
                yield from validator.descend(instance[i], items_schema, path=i)
                return
    else:
        for i, v in enumerate(instance):
            if not isinstance(v, accepted_types):
                yield from validator.descend(instance[i], items_schema, path=i)
                return


# ---------------------------------------------------------------------------
# Optimized oneOf validator for homogeneous arrays
# ---------------------------------------------------------------------------
# `tDimensionArray` and `tMeasureArray` are defined as oneOf over typed array
# variants (e.g., tNumberArray | tBooleanArray | tStringArray). The default
# oneOf validator validates against the first matching branch, then
# re-validates against ALL remaining branches to confirm uniqueness.
# For large arrays this is extremely wasteful — we can determine the correct
# branch by inspecting the first element's type.

_ARRAY_ONEOF_TYPE_MAP: dict[type, int] = {
    int: 0,  # number branch
    float: 0,  # number branch
    str: 2,  # string branch
    bool: 1,  # boolean branch
}

_original_one_of = jsonschema.validators.Draft202012Validator.VALIDATORS["oneOf"]


def _is_typed_array_oneof(one_of: list[Any]) -> bool:
    """Check if this oneOf matches the tDimensionArray/tMeasureArray pattern."""
    if len(one_of) != 3:
        return False
    for branch in one_of:
        if not isinstance(branch, dict) or "$ref" not in branch:
            return False
        ref = branch["$ref"]
        # All cube.schema oneOf refs look like #/$defs/tNumberArray, etc.
        if not isinstance(ref, str):
            return False
        name = ref.rsplit("/", 1)[-1] if "/" in ref else ""
        if name not in (
            "tNumberArray",
            "tBooleanArray",
            "tStringArray",
            "tNumberOrNullArray",
            "tBooleanOrNullArray",
            "tStringOrNullArray",
        ):
            return False
    return True


def _fast_one_of_validator(
    validator: Any, one_of: Any, instance: Any, schema: Any
) -> Any:
    """oneOf validator that short-circuits for typed array schemas."""
    if isinstance(instance, list) and isinstance(one_of, list):
        # Fast path for tDimensionArray/tMeasureArray oneOf (3 typed array refs).
        if instance and _is_typed_array_oneof(one_of):
            first = instance[0]
            element = first
            if element is None:
                for item in instance:
                    if item is not None:
                        element = item
                        break
            if element is not None:
                branch_idx = _ARRAY_ONEOF_TYPE_MAP.get(type(element))
                if branch_idx is not None:
                    yield from validator.descend(
                        instance, one_of[branch_idx], schema_path=branch_idx
                    )
                    return
        # Fast path for oneOf[tDimensionArray, tFunction]: if instance is a list,
        # it must be the array branch (tFunction is an object).
        elif len(one_of) == 2:
            for idx, branch in enumerate(one_of):
                if isinstance(branch, dict) and "$ref" in branch:
                    ref_name = branch["$ref"].rsplit("/", 1)[-1]
                    if ref_name in (
                        "tDimensionArray",
                        "tMeasureArray",
                        "tNumberArray",
                        "tNumberOrNullArray",
                    ):
                        yield from validator.descend(
                            instance, one_of[idx], schema_path=idx
                        )
                        return

    yield from _original_one_of(validator, one_of, instance, schema)


FastDraft202012Validator = jsonschema.validators.extend(  # type: ignore[no-untyped-call]
    jsonschema.validators.Draft202012Validator,
    validators={
        "items": _fast_items_validator,
        "oneOf": _fast_one_of_validator,
    },
)


def get_schema(schema_path: Path) -> dict[str, Any]:
    with open(get_full_schema_path(schema_path), encoding=DEFAULT_ENCODING) as f:
        return json.load(f)  # type: ignore[no-any-return]


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


_registry: Registry[dict[str, Any]] | None = None


def _schema_content_size(schema: dict[str, Any]) -> int:
    """Approximate content size of a schema's $defs for comparison."""
    defs = schema.get("$defs", {})
    return sum(len(json.dumps(v)) for v in defs.values()) if defs else 0


def _get_registry() -> Registry[dict[str, Any]]:
    """Build a referencing.Registry from all local schemas.

    Some technique schemas bundle extended copies of shared schemas (e.g. core.schema)
    under $defs with their own $id. When a bundled copy is LARGER than the standalone
    (more enum values, more definitions), we use the bundled version so that extended
    schemas take precedence. When a bundled copy is a subset, we keep the standalone.
    """
    global _registry  # noqa: PLW0603
    if _registry is not None:
        return _registry

    schemas_by_id: dict[str, dict[str, Any]] = {}
    sizes_by_id: dict[str, int] = {}

    for schema_file in SCHEMA_DIR_PATH.rglob("*.schema.json"):
        with open(schema_file, encoding=DEFAULT_ENCODING) as f:
            schema = json.load(f)
        schema_id = schema.get("$id")
        if not schema_id:
            continue
        if schema_id not in schemas_by_id:
            schemas_by_id[schema_id] = schema
            sizes_by_id[schema_id] = _schema_content_size(schema)

        for val in schema.get("$defs", {}).values():
            if not isinstance(val, dict) or "$id" not in val:
                continue
            bundled_id = val["$id"]
            bundled_size = _schema_content_size(val)
            if bundled_size > sizes_by_id.get(bundled_id, -1):
                schemas_by_id[bundled_id] = val
                sizes_by_id[bundled_id] = bundled_size

    _registry = Registry().with_resources(
        (
            (sid, Resource.from_contents(s, default_specification=DRAFT202012))
            for sid, s in schemas_by_id.items()
        )
    )
    return _registry


_schema_cache: dict[str, dict[str, Any]] = {}


def _get_schema_by_path(schema_path: Path) -> dict[str, Any]:
    """Load a schema from the schemas/ directory, with caching."""
    key = str(schema_path)
    cached = _schema_cache.get(key)
    if cached is not None:
        return cached
    full_path = SCHEMA_DIR_PATH / schema_path
    with open(full_path, encoding=DEFAULT_ENCODING) as f:
        schema: dict[str, Any] = json.load(f)
    _schema_cache[key] = schema
    return schema


_validator_cache: dict[str, Any] = {}


def _get_validator(schema_path: Path) -> Any:
    """Get a cached validator for a schema path."""
    key = str(schema_path)
    cached = _validator_cache.get(key)
    if cached is not None:
        return cached
    schema = _get_schema_by_path(schema_path)
    registry = _get_registry()
    validator = FastDraft202012Validator(
        schema, registry=registry, format_checker=FORMAT_CHECKER
    )
    _validator_cache[key] = validator
    return validator


def validate_asm_schema(asm_dict: dict[str, Any]) -> None:
    """Validate an ASM dict against schemas with cross-schema $ref resolution."""
    try:
        schema_path = get_schema_path_from_asm(asm_dict)
    except Exception as e:
        msg = f"Failed to retrieve schema for model: {e}"
        raise AllotropeSerializationError(msg) from e

    try:
        validator = _get_validator(schema_path)
        validator.validate(asm_dict)
    except AllotropeValidationError:
        raise
    except Exception as e:
        msg = f"Failed to validate allotrope model against schema: {e}"
        raise AllotropeValidationError(msg) from e
