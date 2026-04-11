"""Main orchestrator: fetch schemas, generate modular Python models.

Uses datamodel-codegen as the core engine with pre-processing (flattening
external refs) and post-processing (frozen decorators, dedup imports,
json_name metadata).

Usage:
    python -m allotropy.schema_gen.generate <schema_url>
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import warnings

from datamodel_code_generator import (
    DataModelType,
    generate,
    InputFileType,
    PythonVersion,
)

from allotropy.schema_gen.fetcher import build_dependency_order, SchemaFetcher
from allotropy.schema_gen.flattener import (
    flatten_external_defs,
    merge_allof_overlays,
    needs_flattening,
    remove_unreferenced_defs,
    strip_asm_keys,
    strip_external_whole_schema_refs,
)
from allotropy.schema_gen.naming import (
    DEFAULT_MODEL_OUTPUT_DIR,
    DEFAULT_SCHEMA_CACHE_DIR,
    schema_url_to_model_file,
    schema_url_to_module_path,
    unit_symbol_to_class_name,
)
from allotropy.schema_gen.post_processor import (
    extract_class_names,
    post_process,
)


def generate_models(
    schema_url: str,
    *,
    output_dir: Path = DEFAULT_MODEL_OUTPUT_DIR,
    cache_dir: Path = DEFAULT_SCHEMA_CACHE_DIR,
    models_package: str = "allotropy.allotrope.models_v2",
) -> list[Path]:
    """Generate modular Python models from an Allotrope schema URL.

    Args:
        schema_url: URL to an ADM schema (GitLab blob/raw or Allotrope URL).
        output_dir: Where to write generated Python files.
        cache_dir: Where to cache downloaded schema JSON files.
        models_package: Python package path for the models root.

    Returns:
        List of generated Python file paths.
    """
    # Phase 1: Fetch schemas
    print(f"Fetching schemas from: {schema_url}")  # noqa: T201
    fetcher = SchemaFetcher(cache_dir=cache_dir)
    schemas = fetcher.fetch_with_dependencies(schema_url)
    print(f"  Found {len(schemas)} schema(s)")  # noqa: T201

    # Phase 2: Determine generation order
    order = build_dependency_order(schemas)
    print("Generation order:")  # noqa: T201
    for i, url in enumerate(order):
        print(f"  {i + 1}. {url}")  # noqa: T201

    # Phase 3: Generate each schema in dependency order
    print("\nGenerating Python modules...")  # noqa: T201
    class_registry: dict[str, str] = {}  # class_name -> module_path
    generated_files: list[Path] = []

    for url in order:
        schema = schemas[url]
        module_path = schema_url_to_module_path(url)
        output_path = schema_url_to_model_file(url, output_dir)

        if _is_units_schema(url):
            source = _generate_units_module(schema)
        else:
            source, processed_schema = _generate_with_datamodel_codegen(
                schema, schemas, output_path
            )
            source = post_process(
                source, processed_schema, class_registry, models_package
            )

        # Update class registry with newly defined classes
        for name in extract_class_names(source):
            if name not in class_registry:
                class_registry[name] = module_path

        # Format with black/ruff
        _write_module(output_path, source)
        _lint_file(output_path)

        generated_files.append(output_path)
        print(f"  Generated: {output_path}")  # noqa: T201

    print(f"\nDone! Generated {len(generated_files)} module(s)")  # noqa: T201
    return generated_files


def _is_units_schema(url: str) -> bool:
    return "units.schema" in url


def _generate_with_datamodel_codegen(
    schema: dict[str, Any],
    all_schemas: dict[str, dict[str, Any]],
    output_path: Path,
) -> tuple[str, dict[str, Any]]:
    """Run datamodel-codegen on a schema and return (source, processed_schema).

    Returns the processed (flattened) schema so post_process can build a
    complete property name map including definitions from external schemas.
    """
    # Pre-process: flatten external $defs refs if needed
    processed = schema
    if needs_flattening(processed):
        processed = flatten_external_defs(processed, all_schemas)

    # Merge allOf compositions (base $ref + technique overlay properties)
    processed = merge_allof_overlays(processed)

    # Remove $defs that are no longer referenced after the merge
    processed = remove_unreferenced_defs(processed)

    # Strip $asm.* metadata keys and neutralize remaining external refs
    processed = strip_asm_keys(processed)
    processed = strip_external_whole_schema_refs(processed)

    # Write to temp file and generate
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fp:
        json.dump(processed, fp, ensure_ascii=False)
        fp.flush()
        tmp_path = Path(fp.name)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=UserWarning,
                message="format of .* not understood",
            )
            generate(
                input_=tmp_path,
                output=output_path,
                output_model_type=DataModelType.DataclassesDataclass,
                input_file_type=InputFileType.JsonSchema,
                base_class="",
                target_python_version=PythonVersion.PY_310,
                use_union_operator=True,
                use_double_quotes=True,
                use_standard_collections=True,
                snake_case_field=True,
                disable_timestamp=True,
            )

        source = output_path.read_text(encoding="utf-8")
    finally:
        tmp_path.unlink(missing_ok=True)

    return source, processed


# ---------------------------------------------------------------------------
# Units module generation (custom, not datamodel-codegen)
# ---------------------------------------------------------------------------


def _generate_units_module(schema: dict[str, Any]) -> str:
    """Generate the units module with HasUnit base class and unit subclasses.

    Units schemas have a unique structure that datamodel-codegen can't handle
    well (def keys are symbols like ``pg/mL``, ``#``, etc.).
    """
    lines: list[str] = [
        "# generated by allotropy.schema_gen",
        "",
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True, kw_only=True)",
        "class HasUnit:",
        "    unit: str",
        "",
        "",
    ]

    used_names: set[str] = {"HasUnit"}
    defs = schema.get("$defs", {})

    for _def_name, def_schema in defs.items():
        if not isinstance(def_schema, dict):
            continue
        const_value = _extract_unit_const(def_schema)
        if const_value is None:
            continue

        class_name = unit_symbol_to_class_name(const_value)

        # Deduplicate with numeric suffix
        base = class_name
        counter = 2
        while class_name in used_names:
            class_name = f"{base}{counter}"
            counter += 1
        used_names.add(class_name)

        # Use repr for the default value, ensure double quotes
        quoted = _dquote(const_value)
        lines.extend(
            [
                "@dataclass(frozen=True, kw_only=True)",
                f"class {class_name}(HasUnit):",
                f"    unit: str = {quoted}",
                "",
                "",
            ]
        )

    # Remove trailing blank lines, add single newline
    while lines and lines[-1] == "":
        lines.pop()
    lines.append("")

    return "\n".join(lines)


def _extract_unit_const(schema: dict[str, Any]) -> str | None:
    """Extract the const unit value from a unit $defs entry."""
    props = schema.get("properties", {})
    unit_prop = props.get("unit", {})
    const: str | None = unit_prop.get("const")
    return const


def _dquote(s: str) -> str:
    """Return a double-quoted Python string literal."""
    if '"' not in s:
        return f'"{s}"'
    # Fall back to single quotes if the string contains double quotes
    return repr(s)


# ---------------------------------------------------------------------------
# File writing and formatting
# ---------------------------------------------------------------------------


def _write_module(path: Path, source: str) -> None:
    """Write a Python module file, creating directories and __init__.py files."""
    _ensure_package_dirs(path.parent)
    path.write_text(source, encoding="utf-8")


def _ensure_package_dirs(directory: Path) -> None:
    """Create directory and all parents, adding __init__.py to each."""
    directory.mkdir(parents=True, exist_ok=True)

    current = directory
    while current != current.parent:
        init_file = current / "__init__.py"
        if not init_file.exists():
            init_file.touch()
        if current.name == "models_v2":
            break
        current = current.parent


def _lint_file(path: Path) -> None:
    """Run ruff and black on a generated file to fix formatting."""
    try:
        subprocess.run(
            ["ruff", "check", "--fix", "--quiet", str(path)],  # noqa: S603, S607
            check=False,
            capture_output=True,
        )
    except FileNotFoundError:
        pass
    try:
        subprocess.run(
            ["black", "--quiet", str(path)],  # noqa: S603, S607
            check=False,
            capture_output=True,
        )
    except FileNotFoundError:
        pass


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        msg = (
            "Usage: python -m allotropy.schema_gen.generate <schema_url>\n"
            "\n"
            "Example:\n"
            "  python -m allotropy.schema_gen.generate"
            ' "https://gitlab.com/allotrope-public/asm/-/blob/main/'
            "json-schemas/adm/spectrophotometry/REC/2024/06/"
            'spectrophotometry.schema.json"'
        )
        print(msg)  # noqa: T201
        sys.exit(1)

    schema_url = sys.argv[1]
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MODEL_OUTPUT_DIR
    generate_models(schema_url, output_dir=output_dir)


if __name__ == "__main__":
    main()
