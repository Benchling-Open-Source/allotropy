from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import inspect
import json
import logging
from pathlib import Path
import sys
import types
from types import ModuleType
import typing
from typing import Any, get_args, get_origin


def _to_space_separated(name: str) -> str:
    return name.replace("_", " ").strip().lower()


def _load_module_from_path(module_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_path.stem, str(module_path))
    if spec is None or spec.loader is None:
        msg = f"Unable to load module from {module_path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_path.stem] = module
    spec.loader.exec_module(module)
    return module


def _is_dataclass_type(tp: Any) -> bool:
    try:
        return inspect.isclass(tp) and dataclasses.is_dataclass(tp)
    except Exception:
        return False


def _unwrap_optional(tp: Any) -> Any:
    origin = get_origin(tp)
    if origin is None:
        return tp
    if origin is list or origin is dict or origin is tuple:
        return tp
    if (
        origin is typing.Union
        or str(origin) == "typing.Union"
        or (getattr(types, "UnionType", None) is not None and origin is types.UnionType)
    ):
        args = [a for a in get_args(tp) if a is not type(None)]
        return args[0] if args else tp
    return tp


def _choose_union_member(tp: Any) -> Any:
    origin = get_origin(tp)
    if origin is None:
        return tp
    if (
        origin is typing.Union
        or str(origin) == "typing.Union"
        or (getattr(types, "UnionType", None) is not None and origin is types.UnionType)
    ):
        args = list(get_args(tp))
        # Prefer primitives over dataclasses for friendly fake data
        for preferred in (str, int, float, bool):
            if preferred in args:
                return preferred
        for arg in args:
            if arg is not type(None):
                return arg
    return tp


def _unit_string_from_quantity_type(tp: Any) -> str | None:
    # Quantity types in this codebase subclass a Units class from
    # allotropy.allotrope.models.shared.definitions.units which has a default 'unit' value.
    try:
        for base in getattr(tp, "__mro__", []):
            # Skip the quantity base itself; we need the units mixin
            if base is tp:
                continue
            # Heuristic: a dataclass with a 'unit' field default on the class
            if dataclasses.is_dataclass(base) and any(
                f.name == "unit" for f in dataclasses.fields(base)
            ):
                # Try to read class attribute default, else instantiate
                val = getattr(base, "unit", None)
                if isinstance(val, str) and val:
                    return val
                try:
                    instance = base()
                    val2 = getattr(instance, "unit", None)
                    if isinstance(val2, str) and val2:
                        return val2
                except Exception as exc:
                    logging.debug("Ignoring unit mixin instantiation error: %s", exc)
                    continue
        return None
    except Exception:
        return None


def _fake_scalar_for_type(
    tp: Any, field_name: str, ctx: dict[str, Any] | None = None
) -> Any:
    lname = field_name.lower()
    if "identifier" in lname:
        base = field_name.replace("_", "-").lower()
        idx = None if ctx is None else ctx.get("list_index")
        if isinstance(idx, int):
            return f"{base}-{idx + 1:03d}"
        return f"{base}-001"
    # TStringValue, TClass, TNamed → str (these are unions including str)
    if tp in (str,):
        # Make the fake a bit readable from the field context
        return f"example {field_name.replace('_', ' ')}"
    if tp in (int,):
        return 1
    if tp in (float,):
        return 1.0
    if tp in (bool,):
        return True
    return f"example {field_name.replace('_', ' ')}"


def _fake_for_type(tp: Any, field_name: str, ctx: dict[str, Any] | None = None) -> Any:
    # Resolve Optional/Union
    tp = _choose_union_member(tp)
    tp = _unwrap_optional(tp)

    origin = get_origin(tp)
    args = get_args(tp)

    # Lists
    if origin is list and args:
        inner = args[0]
        items = []
        for i in range(2):
            child_ctx = {} if ctx is None else dict(ctx)
            child_ctx["list_index"] = i
            # If the inner is a dataclass, delegate to dataclass builder to ensure nested structure
            if _is_dataclass_type(_unwrap_optional(_choose_union_member(inner))):
                items.append(
                    _build_object_for_dataclass(
                        _unwrap_optional(_choose_union_member(inner)), child_ctx
                    )
                )
            else:
                items.append(_fake_for_type(inner, field_name, child_ctx))
        return items

    # Dataclasses (including nested models and quantity values)
    if _is_dataclass_type(tp):
        # Quantity-like dataclasses: look for 'value' and 'unit' fields (from TQuantityValue)
        try:
            field_names = [f.name for f in dataclasses.fields(tp)]
            if "value" in field_names and "unit" in field_names:
                unit = _unit_string_from_quantity_type(tp) or "unit"
                return {"value": 1.0, "unit": unit}
        except Exception as exc:
            logging.debug("Dataclass field inspection failed: %s", exc)
        # Generic nested dataclass: return its object (without wrapping in the class name)
        return _build_object_for_dataclass(tp, ctx)

    # Parameterized types we don't explicitly handle: fall back
    if origin is not None:
        return f"example {field_name.replace('_', ' ')}"

    # Primitive or aliases that resolve to primitives
    return _fake_scalar_for_type(tp, field_name, ctx)


def _build_object_for_dataclass(
    cls: type[Any], ctx: dict[str, Any] | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    # Resolve postponed annotations so we get real types instead of strings
    try:
        module_globals = sys.modules.get(cls.__module__).__dict__
    except Exception:
        module_globals = None
    try:
        # include_extras preserves typing like list[Foo] etc.
        type_hints = typing.get_type_hints(
            cls, globalns=module_globals, localns=module_globals, include_extras=True
        )
    except Exception:
        type_hints = {}
    for f in dataclasses.fields(cls):
        key = _to_space_separated(f.name)
        # If there is a non-None default (e.g., manifest), keep it
        if f.default is not dataclasses.MISSING and f.default is not None:
            result[key] = f.default
            continue
        annotated_type = type_hints.get(f.name, f.type)
        result[key] = _fake_for_type(annotated_type, f.name, ctx)
    return result


def generate_fake_json(
    module_file: Path, top_class_name: str = "Model"
) -> dict[str, Any]:
    # Ensure repo 'src' is on sys.path so imports inside the model module work
    src_dir = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(src_dir))

    module = _load_module_from_path(module_file)
    model_cls = getattr(module, top_class_name, None)
    if model_cls is None or not _is_dataclass_type(model_cls):
        msg = f"Dataclass '{top_class_name}' not found in {module_file}"
        raise RuntimeError(msg)
    payload = _build_object_for_dataclass(model_cls)
    # Return the model's fields at the top level (no top-level 'model' key)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a fake JSON document from a dataclasses module (top class 'Model')."
    )
    parser.add_argument(
        "--module-file",
        required=True,
        type=Path,
        help="Path to the Python module containing the generated dataclasses (e.g., mass_spectrometry.py)",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to write the resulting JSON file.",
    )
    parser.add_argument(
        "--top-class",
        default="Model",
        help="Top-level dataclass name to start from. Defaults to 'Model'.",
    )
    args = parser.parse_args()

    data = generate_fake_json(args.module_file, args.top_class)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
