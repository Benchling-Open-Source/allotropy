"""Main orchestrator: fetch schemas, generate modular Python models.

Uses a custom code generator (codegen.py) to produce modular Python
dataclass modules from Allotrope JSON schemas. Core types are defined
once in shared modules; technique schemas import from them.

Usage:
    python -m allotropy.schema_gen.generate <schema_url>
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Any

from allotropy.schema_gen.codegen import SchemaCodeGenerator
from allotropy.schema_gen.fetcher import build_dependency_order, SchemaFetcher
from allotropy.schema_gen.naming import (
    DEFAULT_MODEL_OUTPUT_DIR,
    DEFAULT_SCHEMA_CACHE_DIR,
    schema_url_to_model_file,
    unit_symbol_to_class_name,
)


def generate_models(
    schema_urls: str | list[str],
    *,
    output_dir: Path = DEFAULT_MODEL_OUTPUT_DIR,
    cache_dir: Path = DEFAULT_SCHEMA_CACHE_DIR,
    models_package: str = "allotropy.allotrope.models_v2",
) -> list[Path]:
    """Generate modular Python models from one or more Allotrope schema URLs.

    When multiple URLs are provided, schemas are fetched and merged so that
    shared modules (core.py, hierarchy.py, etc.) accumulate types from all
    technique schemas in a single pass.

    Args:
        schema_urls: One or more URLs to ADM schemas.
        output_dir: Where to write generated Python files.
        cache_dir: Where to cache downloaded schema JSON files.
        models_package: Python package path for the models root.

    Returns:
        List of generated Python file paths.
    """
    if isinstance(schema_urls, str):
        schema_urls = [schema_urls]

    # Phase 1: Fetch all schemas and merge
    fetcher = SchemaFetcher(cache_dir=cache_dir)
    all_schemas: dict[str, Any] = {}
    for url in schema_urls:
        print(f"Fetching schemas from: {url}")  # noqa: T201
        schemas = fetcher.fetch_with_dependencies(url)
        print(f"  Found {len(schemas)} schema(s)")  # noqa: T201
        all_schemas.update(schemas)

    # Phase 1b: Strip embedded $defs with URL keys (BENCHLING schemas bundle
    # copies of dependency schemas as URL-keyed $defs entries). The codegen
    # expects short $defs keys; the full schemas are already fetched separately.
    for schema in all_schemas.values():
        _strip_embedded_defs(schema)

    # Phase 2: Determine generation order across all schemas
    order = build_dependency_order(all_schemas)
    print("Generation order:")  # noqa: T201
    for i, url in enumerate(order):
        print(f"  {i + 1}. {url}")  # noqa: T201

    # Phase 3: Separate units schemas (custom generation) from the rest
    units_urls = [u for u in order if _is_units_schema(u)]
    other_urls = [u for u in order if not _is_units_schema(u)]

    print("\nGenerating Python modules...")  # noqa: T201
    generated_files: list[Path] = []

    # Generate units modules (custom generation, not codegen)
    for url in units_urls:
        schema = all_schemas[url]
        output_path = schema_url_to_model_file(url, output_dir)
        source = _generate_units_module(schema)
        _write_module(output_path, source)
        _lint_file(output_path)
        generated_files.append(output_path)
        print(f"  Generated: {output_path}")  # noqa: T201

    # Generate all other modules via the custom code generator
    if other_urls:
        generator = SchemaCodeGenerator(all_schemas, order, models_package)
        modules = generator.generate_all()

        for url in other_urls:
            module = modules[url]
            output_path = schema_url_to_model_file(url, output_dir)
            source = module.render(models_package)
            # Patch TQuantityValue.value to use JsonFloat (float | InvalidJsonFloat)
            # to support NaN/Infinity serialization, matching V1 behavior.
            if "class TQuantityValue:" in source:
                source = _patch_json_float(source)
            _write_module(output_path, source)
            _lint_file(output_path)
            generated_files.append(output_path)
            print(f"  Generated: {output_path}")  # noqa: T201

    print(f"\nDone! Generated {len(generated_files)} module(s)")  # noqa: T201
    return generated_files


def _strip_embedded_defs(schema: dict[str, Any]) -> None:
    """Remove URL-keyed $defs entries from BENCHLING embedded schemas.

    BENCHLING schemas bundle copies of dependency schemas as $defs entries
    whose keys are full URLs (e.g. "http://purl.allotrope.org/..."). These
    are redundant with the separately-fetched dependency schemas and confuse
    the codegen (which expects short definition names as keys). Stripping
    them lets the codegen resolve $refs to the external schema files instead.
    """
    defs = schema.get("$defs", {})
    url_keys = [k for k in defs if k.startswith("http://") or k.startswith("https://")]
    for k in url_keys:
        del defs[k]
    if "$defs" in schema and not schema["$defs"]:
        del schema["$defs"]


def _is_units_schema(url: str) -> bool:
    return "units.schema" in url


def _patch_json_float(source: str) -> str:
    """Patch TQuantityValue.value to use JsonFloat instead of float.

    V1 models use JsonFloat (float | InvalidJsonFloat) to support NaN/Infinity
    serialization. The JSON schema says "type": "number" which maps to float,
    but the allotropy pipeline needs JsonFloat for round-trip fidelity.
    """
    import_line = (
        "from allotropy.allotrope.models.shared.definitions.definitions import (\n"
        "    InvalidJsonFloat,\n"
        ")\n"
        "\n"
        "JsonFloat = float | InvalidJsonFloat\n"
    )
    # Insert after the existing imports block
    source = source.replace(
        "from typing import Any\n",
        "from typing import Any\n\n" + import_line,
    )
    # Replace the value type in TQuantityValue
    source = source.replace(
        "    value: float\n    unit: TUnit",
        "    value: JsonFloat\n    unit: TUnit",
    )
    return source


# ---------------------------------------------------------------------------
# Units module generation (custom, not codegen)
# ---------------------------------------------------------------------------


def _generate_units_module(schema: dict[str, Any]) -> str:
    """Generate the units module with HasUnit base class and unit subclasses.

    Units schemas have a unique structure that needs special handling
    (def keys are symbols like ``pg/mL``, ``#``, etc.).
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
            "Usage: python -m allotropy.schema_gen.generate <schema_url> [schema_url ...]\n"
            "\n"
            "Multiple URLs can be provided to generate all schemas in a single pass,\n"
            "ensuring shared modules (core.py) accumulate types from all schemas.\n"
            "\n"
            "Example:\n"
            "  python -m allotropy.schema_gen.generate"
            ' "https://gitlab.com/allotrope-public/asm/-/blob/main/'
            "json-schemas/adm/spectrophotometry/REC/2024/06/"
            'spectrophotometry.schema.json"'
        )
        print(msg)  # noqa: T201
        sys.exit(1)

    schema_urls = sys.argv[1:]
    generate_models(schema_urls)


if __name__ == "__main__":
    main()
