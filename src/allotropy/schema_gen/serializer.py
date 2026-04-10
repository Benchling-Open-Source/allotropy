"""Serialize and deserialize ASM model instances to/from JSON-compatible dicts.

Uses the ``json_name`` metadata on dataclass fields (set by the code generator)
to map between Python attribute names and the original JSON property names
defined in the Allotrope schemas.

Usage::

    from allotropy.schema_gen.serializer import to_dict, from_dict
    from allotropy.allotrope.models_v2.adm.spectrophotometry.rec._2024._06.spectrophotometry import Model

    model = Model(asm_manifest="http://...", ...)
    json_dict = to_dict(model)          # Python → JSON dict (schema property names)
    model2 = from_dict(json_dict, Model)  # JSON dict → Python model
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, get_args, get_origin, TypeVar

T = TypeVar("T")


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
                continue
            json_key = f.metadata.get("json_name", f.name)
            result[json_key] = to_dict(value)
        return result

    if isinstance(obj, list):
        return [to_dict(item) for item in obj]

    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}

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
        return data  # type: ignore[return-value]

    # Build reverse mapping: json_name → (python_field_name, field_type)
    json_to_field: dict[str, tuple[str, Any]] = {}
    for f in fields(cls):
        json_key = f.metadata.get("json_name", f.name)
        json_to_field[json_key] = (f.name, f.type)

    kwargs: dict[str, Any] = {}
    for json_key, value in data.items():
        if json_key not in json_to_field:
            continue
        field_name, field_type = json_to_field[json_key]
        kwargs[field_name] = _structure_value(value, field_type, cls)

    return cls(**kwargs)


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

    # Handle Optional (X | None) — unwrap to the non-None type
    if _is_union(origin, field_type):
        non_none_types = [a for a in args if a is not type(None)]
        if non_none_types:
            return _structure_value(value, non_none_types[0], parent_cls)

    # Handle dataclass types
    if is_dataclass(field_type) and isinstance(value, dict):
        return from_dict(value, field_type)

    return value


def _is_union(origin: Any, _field_type: Any) -> bool:
    """Check if a type is a Union / X | Y type."""
    import types
    return origin is types.UnionType


def _resolve_string_annotation(annotation: str, cls: type) -> Any | None:
    """Resolve a string type annotation to an actual type.

    Uses the module where the class is defined to look up the name.
    """
    import sys

    # Strip Optional wrapper patterns like "X | None"
    annotation = annotation.strip()
    if annotation.endswith("| None"):
        inner = annotation[:-len("| None")].strip()
        resolved = _resolve_string_annotation(inner, cls)
        if resolved is not None:
            return resolved | None
        return None

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
    builtins = {"str": str, "int": int, "float": float, "bool": bool}
    return builtins.get(annotation)
