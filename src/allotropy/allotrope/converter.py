from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, field, fields, is_dataclass, make_dataclass, MISSING
from enum import Enum
import keyword
import sys
import types
from typing import Any, get_args, get_origin, get_type_hints, TypeVar, Union

from allotropy.allotrope.path_util import get_model_class_from_schema
from allotropy.schema_gen.naming import default_json_name

T = TypeVar("T")
ModelClass = TypeVar("ModelClass")

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


# ---------------------------------------------------------------------------
# Custom information document helpers
# ---------------------------------------------------------------------------


def _convert_model_key_to_dict_key(key: str) -> str:
    """Decode a Python-safe field name back to the original JSON key."""
    if key.startswith("_KW"):
        key = key[3:]
    if key.startswith("___") and key[3].isdigit():
        key = key[3:]
    for dict_val, model_val in DICT_KEY_TO_MODEL_KEY_REPLACEMENTS.items():
        key = key.replace(model_val, dict_val)
    return key


def _convert_dict_to_model_key(key: str) -> str:
    if keyword.iskeyword(key):
        key = f"_KW{key}"
    if key[0].isdigit():
        key = f"___{key}"
    for dict_val, model_val in DICT_KEY_TO_MODEL_KEY_REPLACEMENTS.items():
        key = key.replace(dict_val, model_val)
    return key


def _unstructure_custom_information_document(model: Any) -> dict[str, Any]:
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


def _custom_info_doc_eq(self: Any, other: Any) -> bool:
    if not is_dataclass(other):
        return NotImplemented
    return asdict(self) == asdict(other)


def structure_custom_information_document(val: dict[str, Any], name: str) -> Any:
    structured_dict = {}
    for key, value in val.items():
        structured_value = value
        if isinstance(value, list):
            structured_value = [
                (
                    structure_custom_information_document(v, key)
                    if isinstance(v, dict)
                    else v
                )
                for v in value
            ]
        elif isinstance(value, dict):
            structured_value = structure_custom_information_document(value, key)
        structured_dict[_convert_dict_to_model_key(key)] = structured_value

    name = name.title().replace(" ", "")
    # eq=False + custom __eq__ so structure(unstructure(x)) == x holds even
    # though make_dataclass creates a new type on each call.
    cls = make_dataclass(
        name,
        ((k, type(v), field(default=None)) for k, v in structured_dict.items()),
        eq=False,
        namespace={"__eq__": _custom_info_doc_eq},
    )
    return cls(**structured_dict)


def add_custom_information_document(
    model: ModelClass, custom_info_doc: Any
) -> ModelClass:
    if not custom_info_doc:
        return model

    # Convert to a dictionary first, so we can clean up values.
    if is_dataclass(custom_info_doc):
        custom_info_dict = asdict(custom_info_doc)
    elif isinstance(custom_info_doc, dict):
        custom_info_dict = custom_info_doc
    else:
        msg = f"Invalid custom_info_doc: {custom_info_doc}"
        raise ValueError(msg)

    # Remove None and {"value": None, "unit"...} values
    cleaned_dict = {}
    for key, value in custom_info_dict.items():
        if value is None:
            continue
        if isinstance(value, dict) and "value" in value and value["value"] is None:
            continue
        cleaned_dict[key] = value

    # If dict is empty after cleaning, do not attach.
    if not cleaned_dict:
        return model

    custom_info_doc = structure_custom_information_document(
        cleaned_dict, "custom information document"
    )

    try:
        model.custom_information_document = custom_info_doc  # type: ignore
    except AttributeError:
        # Frozen dataclasses block __setattr__; bypass with object.__setattr__
        object.__setattr__(model, "custom_information_document", custom_info_doc)
    return model


# ---------------------------------------------------------------------------
# unstructure (model → dict)
# ---------------------------------------------------------------------------


def unstructure(obj: Any) -> Any:
    """Convert a dataclass instance to a JSON-compatible dict.

    - Dataclass fields are keyed by their ``json_name`` metadata (falling back
      to ``field_name.replace("_", " ")``).
    - ``None`` values on optional fields are omitted.
    - Lists and dicts are recursed into.
    - Enum values serialize as their value.
    - Dynamically-attached ``custom_information_document`` attributes are
      included at every nesting level.
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
            result[json_key] = unstructure(value)
        # Handle dynamically-attached custom_information_document (not in fields())
        field_names = {f.name for f in fields(obj)}
        if (
            hasattr(obj, "custom_information_document")
            and "custom_information_document" not in field_names
            and not isinstance(obj.custom_information_document, list)
        ):
            result[
                "custom information document"
            ] = _unstructure_custom_information_document(
                obj.custom_information_document
            )
        return result

    if isinstance(obj, list):
        # Fast-path: lists of primitives (e.g., data cube float arrays with millions
        # of elements) pass through unchanged — return directly to avoid per-element
        # function call overhead.
        if obj:
            first = obj[0]
            if (
                first is None or isinstance(first, int | float | str | bool)
            ) and not isinstance(first, Enum):
                return obj
        return [unstructure(item) for item in obj]

    if isinstance(obj, dict):
        return {k: unstructure(v) for k, v in obj.items()}

    # Enum values: serialize as their value
    if isinstance(obj, Enum):
        return obj.value

    # Primitives: str, int, float, bool
    return obj


# ---------------------------------------------------------------------------
# structure (dict → model)
# ---------------------------------------------------------------------------


def structure(data: Mapping[str, Any] | Any, cls: type[T] | None = None) -> T:
    """Construct a dataclass instance from a JSON-compatible dict.

    Performs the inverse of ``unstructure``: maps JSON property names back to
    Python field names using the ``json_name`` metadata, and recursively
    structures nested dataclasses and lists.

    Dynamically-attached ``custom_information_document`` dicts are
    reconstructed and attached to the result.
    """
    if cls is None:
        cls = get_model_class_from_schema(data)

    if not is_dataclass(cls):
        return data  # type: ignore[return-value]

    if not isinstance(data, dict):
        return data  # type: ignore[return-value]

    # Build reverse mapping: json_name → (python_field_name, field_type)
    # Use get_type_hints to resolve string annotations from __future__ annotations.
    # Fall back to raw f.type strings for dynamic dataclasses where resolution fails.
    try:
        resolved_hints = get_type_hints(cls)
    except (NameError, AttributeError):
        resolved_hints = {}
    json_to_field: dict[str, tuple[str, Any]] = {}
    for f in fields(cls):
        json_key = f.metadata.get("json_name", default_json_name(f.name))
        field_type = resolved_hints.get(f.name, f.type)
        json_to_field[json_key] = (f.name, field_type)

    kwargs: dict[str, Any] = {}
    for json_key, value in data.items():
        if json_key not in json_to_field:
            continue
        field_name, field_type = json_to_field[json_key]
        kwargs[field_name] = _structure_value(value, field_type, cls)

    result = cls(**kwargs)

    # Reconstruct dynamically-attached custom_information_document
    custom_info = data.get("custom information document")
    if custom_info is not None and isinstance(custom_info, dict):
        result = add_custom_information_document(result, custom_info)

    return result  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# structure helpers
# ---------------------------------------------------------------------------


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
        return structure(value, field_type)

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
