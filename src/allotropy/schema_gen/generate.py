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
    ALLOTROPE_URL_PREFIX,
    DEFAULT_MODEL_OUTPUT_DIR,
    DEFAULT_SCHEMA_CACHE_DIR,
    normalize_schema_url,
    schema_url_to_model_file,
    unit_symbol_to_class_name,
    UNITS_SCHEMA_MARKER,
)

# Relative path within the models output_dir for the shared quantity_values module
_QUANTITY_VALUES_REL = Path("shared/definitions/quantity_values.py")

# Relative path within the models output_dir for the shared units module
_SHARED_UNITS_REL = Path("shared/definitions/units.py")

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

    # Snapshot the requested URLs (+ their $ref deps) before loading extras.
    # Only these will be written to disk; cached BENCHLING schemas loaded
    # below contribute their $defs additions but are not regenerated.
    requested_urls = set(all_schemas.keys())

    # Phase 1a: Ensure all cached BENCHLING technique schemas are loaded.
    # BENCHLING schemas embed additions to shared schemas (core/hierarchy) as
    # URL-keyed $defs.  If only a subset of BENCHLING schemas are requested on
    # the command line, the fork step would produce incomplete shared modules
    # (missing additions from other BENCHLING schemas).  Loading them all from
    # cache ensures the forked shared schemas are always complete.
    _load_cached_benchling_schemas(all_schemas, cache_dir)

    # Phase 1b: BENCHLING schemas embed modified copies of dependency schemas
    # as URL-keyed $defs entries.  Instead of merging those additions into the
    # REC shared schemas (which would make REC output depend on which BENCHLING
    # schemas are present), we fork them as standalone BENCHLING-versioned
    # schemas and rewrite $refs so BENCHLING techniques reference their own
    # shared dependency chain.
    _fork_benchling_shared_schemas(all_schemas)

    # Forking may create new BENCHLING-versioned shared schemas (e.g.,
    # core/BENCHLING/2024/09/hierarchy) that the requested techniques depend
    # on.  Include those in the generation set.
    requested_urls.update(
        url for url in all_schemas if url not in requested_urls and "/core/" in url
    )

    # Phase 2: Determine generation order across all schemas
    order = build_dependency_order(all_schemas)
    print("Generation order:")  # noqa: T201
    for i, url in enumerate(order):
        print(f"  {i + 1}. {url}")  # noqa: T201

    # Phase 3: Separate units schemas from the rest (units go to shared module)
    # Only generate modules for requested schemas (+ forked shared schemas).
    other_urls = [u for u in order if not _is_units_schema(u) and u in requested_urls]

    # Update shared units module with any new units from these schemas
    new_unit_count = _update_shared_units(all_schemas, cache_dir, output_dir)
    if new_unit_count:
        print(  # noqa: T201
            f"  Added {new_unit_count} new unit(s) to {output_dir / _SHARED_UNITS_REL}"
        )

    print("\nGenerating Python modules...")  # noqa: T201
    generated_files: list[Path] = []

    # Collect descriptive unit names for TQuantityValue class naming
    unit_descriptive_names = _collect_all_units(all_schemas, cache_dir)

    # Generate all non-units modules via the custom code generator
    if other_urls:
        generator = SchemaCodeGenerator(
            all_schemas,
            order,
            models_package,
            unit_descriptive_names=unit_descriptive_names,
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

        # Regenerate quantity_values.py from the complete unit list.
        # This is always deterministic regardless of which schemas are
        # being generated, because _collect_all_units scans all cached
        # schema files on disk.
        qv_path = _regenerate_quantity_values(
            unit_descriptive_names, _NULLABLE_UNITS, output_dir
        )
        print(f"  Updated {qv_path}")  # noqa: T201

    print(f"\nDone! Generated {len(generated_files)} module(s)")  # noqa: T201
    return generated_files


# ---------------------------------------------------------------------------
# BENCHLING shared schema forking
# ---------------------------------------------------------------------------


def _load_cached_benchling_schemas(
    all_schemas: dict[str, Any], cache_dir: Path
) -> None:
    """Load all cached BENCHLING technique schemas into *all_schemas*.

    This ensures that every BENCHLING schema's embedded ``$defs`` additions
    are available to ``_fork_benchling_shared_schemas``, regardless of which
    schemas were requested on the command line.  Without this, generating a
    single BENCHLING technique could produce incomplete shared modules.
    """
    adm_dir = cache_dir / "adm"
    if not adm_dir.is_dir():
        return

    for schema_file in sorted(adm_dir.rglob("*.schema.json")):
        # Only BENCHLING technique schemas (not core/qudt)
        parts = schema_file.relative_to(cache_dir).parts
        if "BENCHLING" not in parts:
            continue
        # Skip core and qudt (shared, not technique)
        if parts[1] in ("core", "qudt"):
            continue

        # Build canonical URL from cache path
        rel = str(schema_file.relative_to(cache_dir))
        # Remove .json extension for canonical form
        if rel.endswith(".json"):
            rel = rel[:-5]
        canonical = ALLOTROPE_URL_PREFIX + rel

        if canonical in all_schemas:
            continue

        with open(schema_file, encoding="utf-8") as f:
            schema = json.load(f)

        # Only load if it has URL-keyed $defs (i.e., embeds shared schema additions)
        if _has_url_keyed_defs(schema):
            all_schemas[canonical] = schema


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

# Units that need TNullableQuantityValue variants.  Only create nullable
# variants for units that are actually used somewhere; generating nullable
# for all ~780 units is wasteful.  "(unitless)" comes from schemas;
# the others are used by manual parser code (e.g., roche_cedex_bioht).
_NULLABLE_UNITS: list[str] = [
    "(unitless)",
    "g/L",
    "mmol/L",
    "U/L",
]

# Regex to parse existing unit classes from shared/definitions/units.py.
_UNIT_CLASS_RE = re.compile(
    r"^class (\w+)\(HasUnit\):\s*\n\s+unit:\s+str\s*=\s*(?:UNITLESS|\"([^\"]*)\"|'([^']*)')",
    re.MULTILINE,
)


def _read_existing_unit_classes(
    output_dir: Path = DEFAULT_MODEL_OUTPUT_DIR,
) -> dict[str, str]:
    """Read {const_value: class_name} from the current shared units file."""
    units_file = output_dir / _SHARED_UNITS_REL
    if not units_file.exists():
        return {}
    content = units_file.read_text(encoding="utf-8")
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

    iri: str = def_schema.get("properties", {}).get("unit", {}).get("$asm.unit-iri", "")
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


def _update_shared_units(
    all_schemas: dict[str, Any],
    cache_dir: Path,
    output_dir: Path = DEFAULT_MODEL_OUTPUT_DIR,
) -> int:
    """Update shared/definitions/units.py with any new units.

    Returns the number of newly added units.
    """
    all_units = _collect_all_units(all_schemas, cache_dir)
    existing = _read_existing_unit_classes(output_dir)

    new_count = sum(1 for const in all_units if const not in existing)
    if new_count == 0 and existing:
        return 0

    # Regenerate the entire file to maintain sorted order
    units_path = output_dir / _SHARED_UNITS_REL
    source = _generate_shared_units_source(all_units)
    _write_module(units_path, source)
    _lint_file(units_path)
    return new_count


# ---------------------------------------------------------------------------
# Shared quantity_values.py management
# ---------------------------------------------------------------------------


def _regenerate_quantity_values(
    unit_descriptive_names: dict[str, str],
    nullable_units: list[str],
    output_dir: Path = DEFAULT_MODEL_OUTPUT_DIR,
) -> Path:
    """Regenerate quantity_values.py from the complete unit list.

    Builds the file from scratch using ``unit_descriptive_names`` (which
    is derived from all cached schemas, so it's always complete regardless
    of which schemas are being generated in this run).

    Returns the path of the written file.
    """
    lines: list[str] = [
        "# THIS IS AN AUTOGENERATED FILE. DO NOT EDIT THIS FILE DIRECTLY.",
        "# TQuantityValue thin subclasses, one per unit.  Each class inherits from",
        "# TQuantityValue and only overrides the ``unit`` default so that callers",
        "# can write ``TQuantityValueDegreeCelsius(value=42)`` without specifying the unit.",
        "#",
        "# Generated core modules (core.py) import and re-export the subset they",
        "# need; parsers and schema mappers may also import directly from here.",
        "#",
        "# When the code-generator encounters a unit not yet listed here it will",
        "# regenerate this file automatically.",
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "from allotropy.allotrope.models.shared.definitions.definitions import (",
        "    TNullableQuantityValue,",
        "    TQuantityValue,",
        ")",
        "",
        "# ---------------------------------------------------------------------------",
        "# TQuantityValue subclasses (sorted by class name)",
        "# ---------------------------------------------------------------------------",
    ]

    # Build non-nullable classes for every known unit.
    # Deduplicate by class name — multiple unit strings can map to the same
    # descriptive name (e.g., "ug/µL" and "μg/μL" both → MicrogramPerMicroliter).
    # First writer wins (dict preserves insertion order).
    seen: dict[str, tuple[str, str]] = {}  # class_name → (base, unit_str)
    for unit_str, descriptive in unit_descriptive_names.items():
        name = f"TQuantityValue{descriptive}"
        if name not in seen:
            seen[name] = ("TQuantityValue", unit_str)

    # Build nullable classes for units that need them
    for unit_str in nullable_units:
        nullable_desc = unit_descriptive_names.get(unit_str)
        if nullable_desc is not None:
            name = f"TNullableQuantityValue{nullable_desc}"
            if name not in seen:
                seen[name] = ("TNullableQuantityValue", unit_str)

    # Sort by class name for deterministic output
    for class_name, (base, unit_str) in sorted(seen.items()):
        quoted = _dquote(unit_str)
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
    source = "\n".join(lines)
    qv_path = output_dir / _QUANTITY_VALUES_REL
    _write_module(qv_path, source)
    _lint_file(qv_path)
    return qv_path


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


def _discover_cached_technique_urls(
    cache_dir: Path = DEFAULT_SCHEMA_CACHE_DIR,
) -> list[str]:
    """Build purl URLs for all cached technique schemas (non-core, non-qudt)."""
    adm_dir = cache_dir / "adm"
    if not adm_dir.is_dir():
        return []
    urls: list[str] = []
    for schema_file in sorted(adm_dir.rglob("*.schema.json")):
        parts = schema_file.relative_to(cache_dir).parts
        # Skip core and qudt (shared schemas, not techniques)
        if len(parts) > 1 and parts[1] in ("core", "qudt"):
            continue
        rel = str(schema_file.relative_to(cache_dir))
        if rel.endswith(".json"):
            rel = rel[:-5]
        urls.append(ALLOTROPE_URL_PREFIX + rel)
    return urls


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        msg = (
            "Usage: python -m allotropy.schema_gen.generate [--all] [schema_url ...]\n"
            "\n"
            "  --all    Regenerate all cached technique schemas\n"
            "\n"
            "Multiple URLs can be provided to generate schemas in a single pass.\n"
        )
        print(msg)  # noqa: T201
        sys.exit(1)

    if "--all" in sys.argv:
        schema_urls = _discover_cached_technique_urls()
        print(f"Discovered {len(schema_urls)} cached technique schema(s)")  # noqa: T201
    else:
        schema_urls = sys.argv[1:]
    generate_models(schema_urls)


if __name__ == "__main__":
    main()
