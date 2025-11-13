# ruff: noqa: S603
from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import inspect
from pathlib import Path
import subprocess
import sys
import types
import typing
from typing import Any, get_args, get_origin


def _module_from_path(module_path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_path.stem, str(module_path))
    if spec is None or spec.loader is None:
        msg = f"Unable to load module from {module_path}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_path.stem] = module
    spec.loader.exec_module(module)
    return module


def _compute_dotted_import(module_path: Path) -> str:
    # Try to compute dotted path relative to repo's src directory
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    try:
        rel = module_path.resolve().relative_to(src_dir.resolve())
        dotted = ".".join(rel.with_suffix("").parts)
        return dotted
    except Exception:
        # Fallback: use module name only (may fail if not on sys.path)
        return module_path.stem


def _is_dataclass_type(tp: Any) -> bool:
    try:
        return inspect.isclass(tp) and dataclasses.is_dataclass(tp)
    except Exception:
        return False


def _unwrap_optional(tp: Any) -> Any:
    origin = get_origin(tp)
    if origin is None:
        return tp
    if origin in (list, dict, tuple):
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
        for preferred in (str, int, float, bool):
            if preferred in args:
                return preferred
        for arg in args:
            if arg is not type(None):
                return arg
    return tp


def _collect_dataclass_types(
    cls: type[Any], seen: set[type[Any]] | None = None
) -> set[type[Any]]:
    if seen is None:
        seen = set()
    if cls in seen:
        return seen
    seen.add(cls)
    try:
        type_hints = typing.get_type_hints(cls, include_extras=True)
    except Exception:
        type_hints = {}
    for f in dataclasses.fields(cls):
        tp = type_hints.get(f.name, f.type)
        tp = _choose_union_member(tp)
        tp = _unwrap_optional(tp)
        origin = get_origin(tp)
        args = get_args(tp)
        if origin is list and args:
            inner = _unwrap_optional(_choose_union_member(args[0]))
            if _is_dataclass_type(inner):
                _collect_dataclass_types(inner, seen)
        elif _is_dataclass_type(tp):
            _collect_dataclass_types(tp, seen)
    return seen


def _py_literal_for_scalar(tp: Any, field_name: str, list_index: int | None) -> str:
    lname = field_name.lower()
    if "identifier" in lname:
        suffix = (list_index + 1) if isinstance(list_index, int) else 1
        base = field_name.replace("_", "-").lower()
        return f'"{base}-{suffix:03d}"'
    if tp is str:
        return f'"example {field_name.replace("_", " ")}"'
    if tp is int:
        return "1"
    if tp is float:
        return "1.0"
    if tp is bool:
        return "True"
    return f'"example {field_name.replace("_", " ")}"'


def _render_value_expr(
    tp: Any, field_name: str, indent: int, list_index: int | None
) -> str:
    tp = _choose_union_member(tp)
    tp = _unwrap_optional(tp)
    origin = get_origin(tp)
    args = get_args(tp)
    sp = " " * indent
    # Dicts: generate one representative key/value pair
    if origin is dict and args:
        _, val_tp = args[0], args[1]
        key_expr = _py_literal_for_scalar(str, f"{field_name}_key", list_index)
        val_expr = _render_value_expr(
            val_tp, f"{field_name}_value", indent + 4, list_index
        )
        return "{\n" + f"{sp}    {key_expr}: {val_expr}\n" + f"{sp}" + "}"
    if origin is list and args:
        inner = args[0]
        items = []
        for i in range(2):
            items.append(_render_value_expr(inner, field_name, indent + 4, i))
        # Determine if items are multiline (start with a class constructor or open bracket)
        multiline = any(
            x.strip().startswith(tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
            or x.strip().startswith("[")
            or "\n" in x
            for x in items
        )
        if multiline:
            inner_joined = ",\n".join(items)
            return f"[\n{inner_joined}\n{sp}]"
        return f"[{', '.join(items)}]"
    if _is_dataclass_type(tp):
        return _render_dataclass_expr(tp, indent, list_index)
    # scalar
    chosen = _choose_union_member(tp)
    chosen = _unwrap_optional(chosen)
    return _py_literal_for_scalar(chosen, field_name, list_index)


def _render_dataclass_expr(cls: type[Any], indent: int, list_index: int | None) -> str:
    sp = " " * indent
    lines = [f"{sp}{cls.__name__}("]
    try:
        module_globals = sys.modules.get(cls.__module__).__dict__
    except Exception:
        module_globals = None
    try:
        type_hints = typing.get_type_hints(
            cls, globalns=module_globals, localns=module_globals, include_extras=True
        )
    except Exception:
        type_hints = {}
    for f in dataclasses.fields(cls):
        key = f.name
        tp = type_hints.get(f.name, f.type)
        val_expr = _render_value_expr(tp, key, indent + 4, list_index)
        lines.append(f"{sp}    {key}={val_expr},")
    lines.append(f"{sp})")
    return "\n".join(lines)


def generate_dummy_data_py(
    mapper_file: Path, top_class_name: str, output: Path
) -> None:
    # Ensure repo 'src' is on sys.path for module imports
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    module = _module_from_path(mapper_file)

    top_cls = getattr(module, top_class_name, None)
    if top_cls is None or not _is_dataclass_type(top_cls):
        msg = f"Dataclass '{top_class_name}' not found in {mapper_file}"
        raise RuntimeError(msg)

    # Collect all dataclasses used so we can import them in the generated file
    dataclass_types = _collect_dataclass_types(top_cls)
    # Ensure top class first in import list, followed by others sorted
    class_names = [
        top_cls.__name__,
        *sorted([c.__name__ for c in dataclass_types if c is not top_cls]),
    ]

    dotted_import = _compute_dotted_import(mapper_file)
    header = f"""from __future__ import annotations

from dataclasses import asdict
import json

from {dotted_import} import (
    {", ".join(class_names)}
)


def build_dummy_data() -> {top_cls.__name__}:
"""
    body_expr = _render_dataclass_expr(top_cls, indent=4, list_index=None)

    content = header + "    return " + body_expr

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Python file that builds dummy Data-like object for any mapper."
    )
    parser.add_argument(
        "--module-file",
        required=True,
        type=Path,
        help="Path to the mapper module file (e.g., schema_mappers/.../mass_spectrometry.py).",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to write the generated Python file.",
    )
    parser.add_argument(
        "--top-class",
        default="Data",
        help="Top-level dataclass name to start from. Defaults to 'Data'.",
    )
    args = parser.parse_args()
    generate_dummy_data_py(args.module_file, args.top_class, args.output)
    print(f"Wrote dummy data generator to: {args.output}")
    output_path = str(args.output)
    subprocess.run(["ruff", "check", "--fix", output_path], check=True)  # noqa: S607


if __name__ == "__main__":
    main()
