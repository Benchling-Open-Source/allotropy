"""Serialize and deserialize ASM model instances to/from JSON-compatible dicts.

Uses the ``json_name`` metadata on dataclass fields (set by the code generator)
to map between Python attribute names and the original JSON property names
defined in the Allotrope schemas.

Usage::

    from allotropy.schema_gen.serializer import to_dict, from_dict
    from allotropy.allotrope.models.adm.pcr.rec._2024._09.qpcr import Model

    model = Model(asm_manifest="http://...", ...)
    json_dict = to_dict(model)          # Python → JSON dict (schema property names)
    model2 = from_dict(json_dict, Model)  # JSON dict → Python model
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, fields, is_dataclass, MISSING
from enum import Enum
import sys
import types
from typing import Any, get_args, get_origin, TypeVar, Union

from allotropy.schema_gen.naming import default_json_name

T = TypeVar("T")

# Mapping from special characters in JSON keys to safe Python identifiers.
# Used by the custom_information_document structuring/unstructuring logic.
# NOTE: space→"_" MUST be last, or it will break other key replacements.
DICT_KEY_TO_MODEL_KEY_REPLACEMENTS = {
    ".": "_POINT_",
    "-": "_DASH_",
    "°": "_DEG_",
    "/": "_SLASH_",
    "\\": "_BSLASH_",
    "(": "_OPAREN_",
    ")": "_CPAREN_",
    "%": "_PERCENT_",
    ":": "_COLON_",
    "#": "_NUMBER_",
    "[": "_OBRACKET_",
    "]": "_CBRACKET_",
    "$": "_DOLLAR_",
    "~": "_TILDE_",
    "?": "_QMARK_",
    "^": "_CARET_",
    "=": "_EQUALS_",
    "@": "_AT_",
    "'": "_QUOTE_",
    "*": "_ASTERISK_",
    ",": "_COMMA_",
    "&": "_AMPERSAND_",
    " ": "_",
}


def _convert_model_key_to_dict_key(key: str) -> str:
    """Decode a Python-safe field name back to the original JSON key."""
    if key.startswith("_KW"):
        key = key[3:]
    if key.startswith("___") and key[3].isdigit():
        key = key[3:]
    for dict_val, model_val in DICT_KEY_TO_MODEL_KEY_REPLACEMENTS.items():
        key = key.replace(model_val, dict_val)
    return key


def unstructure_custom_information_document(model: Any) -> dict[str, Any]:
    """Serialize a dynamically-created custom_information_document dataclass."""
    required_keys = {a.name for a in fields(model) if a.default == MISSING}

    def dict_factory(kv_pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        return {
            _convert_model_key_to_dict_key(key): (
                value.value if isinstance(value, Enum) else value
            )
            for key, value in kv_pairs
            if key in required_keys or value is not None
        }

    return asdict(model, dict_factory=dict_factory)


def to_dict(obj: Any) -> Any:
    """Convert a dataclass instance to a JSON-compatible dict.

    - Dataclass fields are keyed by their ``json_name`` metadata (falling back
      to the Python attribute name).
    - ``None`` values on optional fields are omitted.
    - Lists are recursed into.
    - Primitives (str, int, float, bool) pass through unchanged.
    """
    if obj is None:
        return None

    if is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {}
        for f in fields(obj):
            value = getattr(obj, f.name)
            if value is None:
                # Keep None for required fields (no default) to preserve
                # explicitly set null values like cycle_threshold_result.
                is_required = f.default is MISSING and f.default_factory is MISSING
                if not is_required:
                    continue
            json_key = f.metadata.get("json_name", default_json_name(f.name))
            result[json_key] = to_dict(value)
        # Handle dynamically-attached custom_information_document (not in fields())
        field_names = {f.name for f in fields(obj)}
        if (
            hasattr(obj, "custom_information_document")
            and "custom_information_document" not in field_names
            and not isinstance(obj.custom_information_document, list)
        ):
            result[
                "custom information document"
            ] = unstructure_custom_information_document(obj.custom_information_document)
        return result

    if isinstance(obj, list):
        return [to_dict(item) for item in obj]

    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}

    # Enum values: serialize as their value
    if isinstance(obj, Enum):
        return obj.value

    # Primitives: str, int, float, bool
    return obj


def from_dict(data: dict[str, Any] | Any, cls: type[T]) -> T:
    """Construct a dataclass instance from a JSON-compatible dict.

    Performs the inverse of ``to_dict``: maps JSON property names back to
    Python field names using the ``json_name`` metadata, and recursively
    structures nested dataclasses and lists.
    """
    if not is_dataclass(cls):
        return data  # type: ignore[return-value]

    if not isinstance(data, dict):
        return data  # type: ignore[no-any-return]

    # Build reverse mapping: json_name → (python_field_name, field_type)
    json_to_field: dict[str, tuple[str, Any]] = {}
    for f in fields(cls):
        json_key = f.metadata.get("json_name", default_json_name(f.name))
        json_to_field[json_key] = (f.name, f.type)

    kwargs: dict[str, Any] = {}
    for json_key, value in data.items():
        if json_key not in json_to_field:
            continue
        field_name, field_type = json_to_field[json_key]
        kwargs[field_name] = _structure_value(value, field_type, cls)

    return cls(**kwargs)  # type: ignore[return-value]


def _structure_value(value: Any, field_type: Any, parent_cls: type) -> Any:
    """Recursively structure a JSON value into the expected Python type."""
    if value is None:
        return None

    # Resolve string type annotations using the parent class's module globals
    if isinstance(field_type, str):
        field_type = _resolve_string_annotation(field_type, parent_cls)
        if field_type is None:
            return value

    origin = get_origin(field_type)
    args = get_args(field_type)

    # Handle list[SomeType]
    if origin is list and args:
        item_type = args[0]
        if isinstance(value, list):
            return [_structure_value(item, item_type, parent_cls) for item in value]
        return value

    # Handle dict[str, Any]
    if origin is dict:
        return value

    # Handle Union types (X | None, X | Y | None, etc.)
    if _is_union(origin):
        non_none_types = [a for a in args if a is not type(None)]
        if len(non_none_types) == 1:
            return _structure_value(value, non_none_types[0], parent_cls)
        # Multiple variant types: try each, preferring those whose shape matches
        for candidate in non_none_types:
            if not _value_matches_type_shape(value, candidate):
                continue
            try:
                return _structure_value(value, candidate, parent_cls)
            except (TypeError, KeyError, ValueError):
                continue
        return value

    # Handle Enum types
    if isinstance(field_type, type) and issubclass(field_type, Enum):
        return field_type(value)

    # Handle dataclass types
    if is_dataclass(field_type) and isinstance(value, dict):
        return from_dict(value, field_type)

    return value


def _value_matches_type_shape(value: Any, field_type: Any) -> bool:
    """Check if a value's shape is compatible with a candidate union variant type."""
    origin = get_origin(field_type)
    if origin is list:
        return isinstance(value, list)
    if is_dataclass(field_type) and isinstance(field_type, type):
        return isinstance(value, dict)
    if isinstance(field_type, type) and issubclass(field_type, Enum):
        return isinstance(value, str | int)
    # Primitive types: check the value actually matches
    if field_type is str:
        return isinstance(value, str)
    if field_type is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if field_type is float:
        return isinstance(value, int | float)
    if field_type is bool:
        return isinstance(value, bool)
    return True


def _is_union(origin: Any) -> bool:
    """Check if a type is a Union / X | Y type."""
    return origin is types.UnionType or origin is Union


def _resolve_string_annotation(annotation: str, cls: type) -> Any | None:
    """Resolve a string type annotation to an actual type.

    Handles simple names (``SomeClass``), generic wrappers (``list[X]``),
    and union syntax (``A | B | None``).  Uses the module where *cls* is
    defined to look up names.
    """

    annotation = annotation.strip()

    # Handle union types: "A | B" or "A | B | None"
    if " | " in annotation:
        parts = [p.strip() for p in annotation.split(" | ")]
        resolved_parts: list[Any] = []
        for part in parts:
            if part == "None":
                resolved_parts.append(type(None))
            else:
                resolved = _resolve_string_annotation(part, cls)
                if resolved is None:
                    return None
                resolved_parts.append(resolved)
        result = resolved_parts[0]
        for t in resolved_parts[1:]:
            result = result | t
        return result

    # Strip list[] wrapper
    if annotation.startswith("list[") and annotation.endswith("]"):
        inner = annotation[5:-1]
        resolved = _resolve_string_annotation(inner, cls)
        if resolved is not None:
            return list[resolved]  # type: ignore[valid-type]
        return None

    # Look up in the class's module
    module = sys.modules.get(cls.__module__)
    if module:
        resolved = getattr(module, annotation, None)
        if resolved is not None:
            return resolved

    # Try builtins
    builtins_map = {"str": str, "int": int, "float": float, "bool": bool}
    return builtins_map.get(annotation)
