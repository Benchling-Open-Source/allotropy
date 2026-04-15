"""Main orchestrator: fetch schemas, generate modular Python models.

Uses a custom code generator (codegen.py) to produce modular Python
dataclass modules from Allotrope JSON schemas. Core types are defined
once in shared modules; technique schemas import from them.

Usage:
    hatch run scripts:generate-schemas <schema_url> [schema_url ...]
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from allotropy.schema_gen.codegen import (
    _dquote,
    extract_unit_const,
    SchemaCodeGenerator,
)
from allotropy.schema_gen.fetcher import build_dependency_order, SchemaFetcher
from allotropy.schema_gen.naming import (
    DEFAULT_MODEL_OUTPUT_DIR,
    DEFAULT_SCHEMA_CACHE_DIR,
    normalize_schema_url,
    schema_url_to_model_file,
    unit_symbol_to_class_name,
    UNITS_SCHEMA_MARKER,
)

# Path to the shared quantity_values module (relative to output_dir's parent)
_QUANTITY_VALUES_FILE = Path(
    "src/allotropy/allotrope/models/shared/definitions/quantity_values.py"
)

# Path to the shared units module
_SHARED_UNITS_FILE = Path("src/allotropy/allotrope/models/shared/definitions/units.py")

# Regex to extract the status/version segment from an Allotrope URL path.
# Matches e.g. "/REC/2024/09/" or "/WD/2025/03/".
_STATUS_VERSION_RE = re.compile(r"/(REC|WD)/(\d{4}/\d{2})/")

# Regex to extract the BENCHLING version from a BENCHLING schema URL.
_BENCHLING_VERSION_RE = re.compile(r"/BENCHLING/(\d{4}/\d{2})/")


def generate_models(
    schema_urls: str | list[str],
    *,
    output_dir: Path = DEFAULT_MODEL_OUTPUT_DIR,
    cache_dir: Path = DEFAULT_SCHEMA_CACHE_DIR,
    models_package: str = "allotropy.allotrope.models",
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

    # Phase 1b: BENCHLING schemas embed modified copies of dependency schemas
    # as URL-keyed $defs entries.  Instead of merging those additions into the
    # REC shared schemas (which would make REC output depend on which BENCHLING
    # schemas are present), we fork them as standalone BENCHLING-versioned
    # schemas and rewrite $refs so BENCHLING techniques reference their own
    # shared dependency chain.
    _fork_benchling_shared_schemas(all_schemas)

    # Phase 2: Determine generation order across all schemas
    order = build_dependency_order(all_schemas)
    print("Generation order:")  # noqa: T201
    for i, url in enumerate(order):
        print(f"  {i + 1}. {url}")  # noqa: T201

    # Phase 3: Separate units schemas from the rest (units go to shared module)
    other_urls = [u for u in order if not _is_units_schema(u)]

    # Update shared units module with any new units from these schemas
    new_unit_count = _update_shared_units(all_schemas, cache_dir)
    if new_unit_count:
        print(  # noqa: T201
            f"  Added {new_unit_count} new unit(s) to {_SHARED_UNITS_FILE}"
        )

    print("\nGenerating Python modules...")  # noqa: T201
    generated_files: list[Path] = []

    # Generate all non-units modules via the custom code generator
    if other_urls:
        existing_unit_to_class = _read_existing_quantity_value_classes()
        generator = SchemaCodeGenerator(
            all_schemas,
            order,
            models_package,
            existing_unit_to_class,
        )
        modules = generator.generate_all()

        for url in other_urls:
            module = modules[url]
            if not module.classes and not module.imports:
                continue
            output_path = schema_url_to_model_file(url, output_dir)
            source = module.render(models_package)
            _write_module(output_path, source)
            _lint_file(output_path)
            generated_files.append(output_path)
            print(f"  Generated: {output_path}")  # noqa: T201

        # Append any newly discovered quantity value types to the shared module
        if generator.new_quantity_value_classes:
            _append_quantity_value_classes(generator.new_quantity_value_classes)
            print(  # noqa: T201
                f"  Added {len(generator.new_quantity_value_classes)} new"
                f" quantity value type(s) to {_QUANTITY_VALUES_FILE}"
            )

    print(f"\nDone! Generated {len(generated_files)} module(s)")  # noqa: T201
    return generated_files


# ---------------------------------------------------------------------------
# BENCHLING shared schema forking
# ---------------------------------------------------------------------------


def _fork_benchling_shared_schemas(all_schemas: dict[str, Any]) -> None:
    """Fork BENCHLING-modified dependency schemas into standalone BENCHLING versions.

    BENCHLING technique schemas embed modified copies of REC/WD shared schemas
    as URL-keyed ``$defs`` entries (keys are full ``http://`` URLs).  These
    copies may add extra properties not in the originals.

    Instead of merging additions into the REC schemas (which would make REC
    output non-deterministic), this function:

    1. Creates a BENCHLING-versioned copy of each modified shared schema
       (deep-merging the REC base with the BENCHLING additions).
    2. Rewrites ``$ref`` strings in the BENCHLING technique schema (and in
       the newly created BENCHLING shared schemas) to point to the forked
       BENCHLING versions.
    3. Strips the URL-keyed ``$defs`` entries.

    For embedded schemas that are already BENCHLING (BENCHLING-to-BENCHLING
    embeddings, e.g., detector sub-schemas), the existing merge-into-standalone
    behavior is preserved since those don't affect REC modules.
    """
    # Collect all schemas that have URL-keyed $defs (the BENCHLING embedders).
    # We snapshot the keys first because we'll be adding new entries to all_schemas.
    embedder_urls = [
        url
        for url, schema in all_schemas.items()
        if _has_url_keyed_defs(schema) and "/BENCHLING/" in url
    ]

    # Global rewrite map: {original_rec_url → new_benchling_url}.
    # Accumulated across all embedders so that cross-schema $ref rewriting
    # covers all forked schemas.
    all_rewrites: dict[str, str] = {}

    for embedder_url in embedder_urls:
        schema = all_schemas[embedder_url]
        benchling_version = _extract_benchling_version(embedder_url)
        if not benchling_version:
            continue

        defs = schema.get("$defs", {})
        url_keys = [
            k for k in defs if k.startswith("http://") or k.startswith("https://")
        ]

        for key in url_keys:
            embedded = defs[key]
            try:
                canonical = normalize_schema_url(key)
            except ValueError:
                continue

            if canonical not in all_schemas:
                continue

            if "/BENCHLING/" in canonical:
                # BENCHLING-to-BENCHLING embedding: merge into the standalone
                # BENCHLING schema (does not affect any REC schema).
                all_schemas[canonical] = _deep_merge(all_schemas[canonical], embedded)
            else:
                # REC/WD embedding: fork as a new BENCHLING-versioned schema.
                benchling_url = _rec_to_benchling_url(canonical, benchling_version)
                if benchling_url in all_schemas:
                    # Another BENCHLING technique with the same version already
                    # forked this schema — accumulate additions.
                    all_schemas[benchling_url] = _deep_merge(
                        all_schemas[benchling_url], embedded
                    )
                else:
                    all_schemas[benchling_url] = _deep_merge(
                        all_schemas[canonical], embedded
                    )
                all_rewrites[canonical] = benchling_url

    # Rewrite $refs in all BENCHLING schemas (technique + forked shared) so
    # they reference the BENCHLING versions instead of the original REC ones.
    for url in list(all_schemas):
        if "/BENCHLING/" not in url:
            continue
        all_schemas[url] = _rewrite_refs(all_schemas[url], all_rewrites)

    # Strip URL-keyed $defs from all schemas (they've been extracted).
    for schema in all_schemas.values():
        _strip_embedded_defs(schema)


def _has_url_keyed_defs(schema: dict[str, Any]) -> bool:
    """Check if a schema has URL-keyed $defs entries."""
    defs = schema.get("$defs", {})
    return any(k.startswith("http://") or k.startswith("https://") for k in defs)


def _extract_benchling_version(url: str) -> str | None:
    """Extract the version (e.g., '2023/09') from a BENCHLING schema URL."""
    m = _BENCHLING_VERSION_RE.search(url)
    return m.group(1) if m else None


def _rec_to_benchling_url(rec_url: str, benchling_version: str) -> str:
    """Convert a REC/WD schema URL to its BENCHLING-versioned counterpart.

    Example:
        rec_url = "http://purl.allotrope.org/json-schemas/adm/core/REC/2024/09/hierarchy.schema"
        benchling_version = "2023/09"
        → "http://purl.allotrope.org/json-schemas/adm/core/BENCHLING/2023/09/hierarchy.schema"
    """
    return _STATUS_VERSION_RE.sub(f"/BENCHLING/{benchling_version}/", rec_url, count=1)


def _rewrite_refs(schema: Any, rewrites: dict[str, str]) -> Any:
    """Recursively rewrite $ref strings in a schema using the rewrite map.

    Each key in *rewrites* is a canonical URL prefix; if a $ref starts with
    that prefix (possibly followed by ``#/$defs/...``), the prefix is replaced
    with the mapped value.
    """
    if isinstance(schema, dict):
        result: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "$ref" and isinstance(value, str):
                result[key] = _apply_ref_rewrite(value, rewrites)
            elif key == "$id" and isinstance(value, str):
                # Also rewrite $id so the schema's self-reference stays consistent
                result[key] = _apply_ref_rewrite(value, rewrites)
            else:
                result[key] = _rewrite_refs(value, rewrites)
        return result
    if isinstance(schema, list):
        return [_rewrite_refs(item, rewrites) for item in schema]
    return schema


def _apply_ref_rewrite(ref: str, rewrites: dict[str, str]) -> str:
    """Apply the first matching rewrite rule to a $ref string."""
    for old_prefix, new_prefix in rewrites.items():
        if ref.startswith(old_prefix):
            return new_prefix + ref[len(old_prefix) :]
        # Also match with .json suffix (some refs include it)
        if ref.startswith(old_prefix + ".json"):
            return new_prefix + ref[len(old_prefix) :]
    return ref


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge *overlay* into *base*, returning a new dict.

    For dict values, recurse.  For everything else, overlay wins.
    """
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


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
    return UNITS_SCHEMA_MARKER in url


# ---------------------------------------------------------------------------
# Shared units.py management
# ---------------------------------------------------------------------------

# Known IRI errors in upstream schemas.  The QUDT IRI for "RU.s" (response
# unit * second) is tagged "ResponseUnitPerSecond" -- but that name belongs
# to "RU/s" (response unit / second).
_IRI_NAME_CORRECTIONS: dict[str, str] = {
    "RU.s": "ResponseUnitTimesSecond",
}

# Units that exist in shared/definitions/units.py but not in any upstream
# schema.  These were added manually for BENCHLING parsers and must survive
# regeneration.
_MANUAL_UNITS: dict[str, str] = {
    "OD": "OpticalDensity",
    "M-1cm-1": "PerMolarPerCentimeter",
    "mm^2": "SquareMillimeter",
    "RU^2": "SquareResponseUnit",
    "TODO": "TODO",
    "U/L": "UnitPerLiter",
}

# Regex to parse existing unit classes from shared/definitions/units.py.
_UNIT_CLASS_RE = re.compile(
    r"^class (\w+)\(HasUnit\):\s*\n\s+unit:\s+str\s*=\s*(?:UNITLESS|\"([^\"]*)\"|'([^']*)')",
    re.MULTILINE,
)


def _read_existing_unit_classes() -> dict[str, str]:
    """Read {const_value: class_name} from the current shared units file."""
    if not _SHARED_UNITS_FILE.exists():
        return {}
    content = _SHARED_UNITS_FILE.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for match in _UNIT_CLASS_RE.finditer(content):
        class_name = match.group(1)
        # group(2) is double-quoted, group(3) is single-quoted
        const = match.group(2) if match.group(2) is not None else match.group(3)
        if const is None:
            # UNITLESS constant reference
            const = "(unitless)"
        result[const] = class_name
    return result


def _extract_descriptive_name(
    const: str, def_schema: dict[str, Any], def_key: str
) -> str:
    """Extract a descriptive class name for a unit from its schema definition.

    Priority:
    1. IRI correction map (fixes known upstream errors)
    2. ``$asm.unit-iri`` fragment (authoritative QUDT name)
    3. Descriptive ``$defs`` key (BENCHLING schemas use CamelCase keys)
    4. Fallback to ``unit_symbol_to_class_name()`` (abbreviated)
    """
    if const in _IRI_NAME_CORRECTIONS:
        return _IRI_NAME_CORRECTIONS[const]

    iri = def_schema.get("properties", {}).get("unit", {}).get("$asm.unit-iri", "")
    if iri and "#" in iri:
        return iri.split("#")[1]

    # BENCHLING schemas use descriptive $defs keys (e.g., "DegreeCelsius")
    if def_key[:1].isupper() and not any(c in def_key for c in "/#%^()"):
        return def_key

    return unit_symbol_to_class_name(const)


def _collect_all_units(all_schemas: dict[str, Any], cache_dir: Path) -> dict[str, str]:
    """Collect all unit symbols from cached qudt schemas + in-memory schemas.

    Returns ``{const_value: descriptive_class_name}``.
    """
    units: dict[str, str] = {}

    def _scan_defs(defs: dict[str, Any]) -> None:
        for key, val in defs.items():
            if not isinstance(val, dict):
                continue
            const = extract_unit_const(val)
            if not const or const in units:
                continue
            units[const] = _extract_descriptive_name(const, val, key)

    # 1. Scan all cached qudt schema files on disk (complete across all versions)
    for schema_file in sorted(cache_dir.rglob("units.schema.json")):
        with open(schema_file, encoding="utf-8") as f:
            schema = json.load(f)
        _scan_defs(schema.get("$defs", {}))

    # 2. Scan embedded unit additions in technique schemas on disk
    adm_dir = cache_dir / "adm"
    if adm_dir.is_dir():
        for schema_file in sorted(adm_dir.rglob("*.json")):
            with open(schema_file, encoding="utf-8") as f:
                schema = json.load(f)
            for key, val in schema.get("$defs", {}).items():
                if "units.schema" in key and isinstance(val, dict):
                    _scan_defs(val.get("$defs", {}))

    # 3. Scan in-memory schemas (includes BENCHLING forks with merged additions)
    for url, schema in all_schemas.items():
        if _is_units_schema(url):
            _scan_defs(schema.get("$defs", {}))

    # 4. Add manual units (BENCHLING-only, not in any schema)
    for const, name in _MANUAL_UNITS.items():
        if const not in units:
            units[const] = name

    return units


def _generate_shared_units_source(all_units: dict[str, str]) -> str:
    """Generate the Python source for shared/definitions/units.py."""
    lines: list[str] = [
        "# THIS IS AN AUTOGENERATED FILE. DO NOT EDIT THIS FILE DIRECTLY.",
        "from dataclasses import dataclass",
        "",
        'UNITLESS = "(unitless)"',
        "",
        "",
        "@dataclass(frozen=True, kw_only=True)",
        "class HasUnit:",
        "    unit: str",
        "",
        "",
    ]

    # Sort entries by class name for deterministic output
    sorted_entries = sorted(all_units.items(), key=lambda x: x[1])

    # Deduplicate class names with numeric suffix
    used_names: set[str] = {"HasUnit"}
    for const, name in sorted_entries:
        class_name = name
        base = class_name
        counter = 2
        while class_name in used_names:
            class_name = f"{base}{counter}"
            counter += 1
        used_names.add(class_name)

        # Unitless uses the module-level constant
        if const == "(unitless)":
            default = "UNITLESS"
        else:
            default = _dquote(const)

        lines.extend(
            [
                "@dataclass(frozen=True, kw_only=True)",
                f"class {class_name}(HasUnit):",
                f"    unit: str = {default}",
                "",
                "",
            ]
        )

    # Remove trailing blank lines, add single newline
    while lines and lines[-1] == "":
        lines.pop()
    lines.append("")

    return "\n".join(lines)


def _update_shared_units(all_schemas: dict[str, Any], cache_dir: Path) -> int:
    """Update shared/definitions/units.py with any new units.

    Returns the number of newly added units.
    """
    all_units = _collect_all_units(all_schemas, cache_dir)
    existing = _read_existing_unit_classes()

    new_count = sum(1 for const in all_units if const not in existing)
    if new_count == 0 and existing:
        return 0

    # Regenerate the entire file to maintain sorted order
    source = _generate_shared_units_source(all_units)
    _write_module(_SHARED_UNITS_FILE, source)
    _lint_file(_SHARED_UNITS_FILE)
    return new_count


# ---------------------------------------------------------------------------
# Shared quantity_values.py management
# ---------------------------------------------------------------------------

_QV_UNIT_RE = re.compile(
    r"^class (T(?:Nullable)?QuantityValue\w+)\([^)]+\):\s*\n"
    r"\s+unit:\s+str\s*=\s*\"([^\"]+)\"",
    re.MULTILINE,
)


def _read_existing_quantity_value_classes() -> dict[tuple[str, bool], str]:
    """Read class names and unit values already defined in quantity_values.py.

    Returns a mapping from ``(unit_string, nullable)`` to class name.
    The *nullable* key distinguishes ``TQuantityValueUnitless`` from
    ``TNullableQuantityValueUnitless`` for the same unit string.
    """
    if not _QUANTITY_VALUES_FILE.exists():
        return {}
    content = _QUANTITY_VALUES_FILE.read_text(encoding="utf-8")
    unit_to_class: dict[tuple[str, bool], str] = {}
    for name, unit in _QV_UNIT_RE.findall(content):
        nullable = name.startswith("TNullableQuantityValue")
        unit_to_class[(unit, nullable)] = name
    return unit_to_class


def _append_quantity_value_classes(new_classes: list[tuple[str, str]]) -> None:
    """Append new TQuantityValue subclasses to quantity_values.py.

    Each entry in *new_classes* is ``(class_name, unit_string)``.
    """
    if not _QUANTITY_VALUES_FILE.exists():
        return

    lines: list[str] = []
    for class_name, unit_str in sorted(new_classes):
        quoted = _dquote(unit_str)
        base = (
            "TNullableQuantityValue"
            if class_name.startswith("TNullableQuantityValue")
            else "TQuantityValue"
        )
        lines.extend(
            [
                "",
                "",
                "@dataclass(frozen=True, kw_only=True)",
                f"class {class_name}({base}):",
                f"    unit: str = {quoted}",
            ]
        )
    lines.append("")

    content = _QUANTITY_VALUES_FILE.read_text(encoding="utf-8")
    # Ensure we append after existing content (with a newline separator)
    if not content.endswith("\n"):
        content += "\n"
    content += "\n".join(lines)
    _QUANTITY_VALUES_FILE.write_text(content, encoding="utf-8")
    _lint_file(_QUANTITY_VALUES_FILE)


# ---------------------------------------------------------------------------
# File writing and formatting
# ---------------------------------------------------------------------------


def _write_module(path: Path, source: str) -> None:
    """Write a Python module file, creating parent directories as needed."""
    _ensure_package_dirs(path.parent)
    path.write_text(source, encoding="utf-8")


def _ensure_package_dirs(directory: Path) -> None:
    """Create directory and all parents."""
    directory.mkdir(parents=True, exist_ok=True)


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
