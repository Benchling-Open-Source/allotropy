"""Post-processing transforms for datamodel-codegen output.

Three independent, mechanical transforms applied in sequence:
1. add_frozen_kw_only — add frozen=True, kw_only=True to dataclass decorators
2. dedup_with_imports — replace duplicate classes with imports from dependency modules
3. add_json_name_metadata — add field(metadata={"json_name": ...}) to all fields
"""

from __future__ import annotations

import re
from typing import Any

from allotropy.schema_gen.naming import property_name_to_python


def post_process(
    source: str,
    schema: dict[str, Any],
    class_registry: dict[str, str],
    models_package: str,
) -> str:
    """Apply all post-processing transforms in order."""
    source = strip_model_any_alias(source)
    source = add_frozen_kw_only(source)
    source = dedup_with_imports(source, class_registry, models_package)
    source = add_json_name_metadata(source, schema)
    source = ensure_field_import(source)
    source = clean_blank_lines(source)
    return source


# ---------------------------------------------------------------------------
# Transform 1: Add frozen/kw_only to dataclass decorators
# ---------------------------------------------------------------------------


def add_frozen_kw_only(source: str) -> str:
    """Replace bare @dataclass with @dataclass(frozen=True, kw_only=True).

    The top-level Model class gets @dataclass(kw_only=True) without frozen.
    """

    def _replacer(m: re.Match[str]) -> str:
        class_name = m.group(1)
        if class_name == "Model":
            return f"@dataclass(kw_only=True)\nclass {class_name}"
        return f"@dataclass(frozen=True, kw_only=True)\nclass {class_name}"

    return re.sub(r"@dataclass\nclass (\w+)", _replacer, source)


# ---------------------------------------------------------------------------
# Transform 2: Replace duplicate classes with imports
# ---------------------------------------------------------------------------


def dedup_with_imports(
    source: str,
    class_registry: dict[str, str],
    models_package: str,
) -> str:
    """Remove classes already defined in dependency modules, add imports."""
    if not class_registry:
        return source

    lines = source.split("\n")
    new_imports: dict[str, set[str]] = {}  # module_path -> {class_names}
    lines_to_remove: set[int] = set()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for type alias: ClassName = ...
        alias_match = re.match(r"^(\w+)\s*=\s*", line)
        if alias_match and not line.startswith("    "):
            name = alias_match.group(1)
            if name in class_registry:
                lines_to_remove.add(i)
                module_path = class_registry[name]
                new_imports.setdefault(module_path, set()).add(name)
                i += 1
                continue

        # Check for class definition with decorator
        if line.startswith("@dataclass"):
            class_line_idx = i + 1
            if class_line_idx < len(lines):
                class_match = re.match(r"class (\w+)", lines[class_line_idx])
                if class_match:
                    name = class_match.group(1)
                    if name in class_registry:
                        # Remove decorator + class + body
                        module_path = class_registry[name]
                        new_imports.setdefault(module_path, set()).add(name)
                        lines_to_remove.add(i)  # decorator
                        lines_to_remove.add(class_line_idx)  # class line
                        j = class_line_idx + 1
                        while j < len(lines) and (
                            lines[j].startswith("    ") or lines[j] == ""
                        ):
                            lines_to_remove.add(j)
                            j += 1
                            # Stop at next non-blank, non-indented line
                            if (
                                j < len(lines)
                                and lines[j] == ""
                                and j + 1 < len(lines)
                                and not lines[j + 1].startswith("    ")
                            ):
                                lines_to_remove.add(j)
                                break
                        i = j
                        continue
        i += 1

    # Build filtered source
    filtered = [line for idx, line in enumerate(lines) if idx not in lines_to_remove]

    # Build import lines
    import_lines: list[str] = []
    for module_path, names in sorted(new_imports.items()):
        sorted_names = sorted(names)
        import_lines.append(
            f"from {models_package}.{module_path} import (\n"
            + "".join(f"    {n},\n" for n in sorted_names)
            + ")"
        )

    if not import_lines:
        return "\n".join(filtered)

    # Insert new imports after existing imports
    result_lines = filtered
    insert_idx = _find_import_insert_point(result_lines)
    for imp_line in reversed(import_lines):
        result_lines.insert(insert_idx, imp_line)

    return "\n".join(result_lines)


def _find_import_insert_point(lines: list[str]) -> int:
    """Find the line index after the last import statement."""
    last_import = 0
    for i, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            last_import = i + 1
        elif line.startswith(")") and i > 0 and "import" in lines[i - 1]:
            last_import = i + 1
        # Handle multi-line imports
        if line.strip() == ")" and last_import > 0:
            # Check if this closes a multi-line import
            for j in range(i - 1, -1, -1):
                if lines[j].startswith("from ") or lines[j].startswith("import "):
                    last_import = i + 1
                    break
                if not lines[j].startswith("    ") and lines[j].strip() != "":
                    break
    return last_import


# ---------------------------------------------------------------------------
# Transform 3: Add json_name metadata to fields
# ---------------------------------------------------------------------------


def add_json_name_metadata(source: str, schema: dict[str, Any]) -> str:
    """Add field(metadata={"json_name": ...}) to all dataclass fields."""
    # Build comprehensive property name map from schema
    name_map = _build_property_name_map(schema)

    # First, normalize multi-line field defaults into single lines
    # e.g., "    field: Type = (\n        None\n    )" → "    field: Type = None"
    source = _join_multiline_defaults(source)

    lines = source.split("\n")
    result: list[str] = []

    for line in lines:
        # Match field lines: "    field_name: Type" or "    field_name: Type = value"
        field_match = re.match(
            r"^(    )(\w+)(:\s*.+?)(?:\s*=\s*(.+))?$",
            line,
        )
        if field_match:
            indent = field_match.group(1)
            field_name = field_match.group(2)
            type_annotation = field_match.group(3)
            default_value = field_match.group(4)

            json_name = name_map.get(field_name)
            if json_name is not None:
                # Escape any double quotes in the json_name
                escaped = json_name.replace('"', '\\"')
                if default_value is not None and default_value.strip() != "None":
                    new_line = (
                        f"{indent}{field_name}{type_annotation} = "
                        f'field(default={default_value.strip()}, metadata={{"json_name": "{escaped}"}})'
                    )
                elif default_value is not None:
                    new_line = (
                        f"{indent}{field_name}{type_annotation} = "
                        f'field(default=None, metadata={{"json_name": "{escaped}"}})'
                    )
                else:
                    new_line = (
                        f"{indent}{field_name}{type_annotation} = "
                        f'field(metadata={{"json_name": "{escaped}"}})'
                    )
                result.append(new_line)
                continue

        result.append(line)

    return "\n".join(result)


def _join_multiline_defaults(source: str) -> str:
    """Join multi-line field default values into single lines.

    datamodel-codegen produces patterns like::

        field_name: Type | None = (
            None
        )

    This normalizes them to ``field_name: Type | None = None``.
    """
    # Pattern: "    name: Type = (" followed by indented lines until "    )"
    lines = source.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check for field with opening paren default
        if re.match(r"^    \w+:.*=\s*\(\s*$", line):
            # Collect lines until closing paren
            # Strip trailing "= (" to get "    name: Type"
            prefix = re.sub(r"\s*=\s*\(\s*$", "", line)
            i += 1
            default_parts: list[str] = []
            while i < len(lines) and not re.match(r"^    \)\s*$", lines[i]):
                default_parts.append(lines[i].strip())
                i += 1
            if i < len(lines):
                i += 1  # skip the closing "    )"
            # Join: "    name: Type = value"
            default_value = " ".join(default_parts) if default_parts else "None"
            result.append(f"{prefix} = {default_value}")
        else:
            result.append(line)
            i += 1
    return "\n".join(result)


def _build_property_name_map(schema: dict[str, Any]) -> dict[str, str]:
    """Build mapping from python_field_name -> json_property_name.

    Walks all properties dicts in the schema tree.
    """
    name_map: dict[str, str] = {}
    _walk_properties(schema, name_map)
    return name_map


def _walk_properties(obj: Any, name_map: dict[str, str]) -> None:
    """Recursively walk schema and collect property name mappings."""
    if not isinstance(obj, dict):
        return

    if "properties" in obj:
        for json_name in obj["properties"]:
            python_name = property_name_to_python(json_name)
            # Only add if we don't have a conflicting entry
            if python_name not in name_map:
                name_map[python_name] = json_name

    # Recurse into all dict values
    for value in obj.values():
        if isinstance(value, dict):
            _walk_properties(value, name_map)
        elif isinstance(value, list):
            for item in value:
                _walk_properties(item, name_map)


# ---------------------------------------------------------------------------
# Helper transforms
# ---------------------------------------------------------------------------


def strip_model_any_alias(source: str) -> str:
    """Remove ``Model = Any`` aliases that datamodel-codegen generates for sub-schemas."""
    return re.sub(r"^Model = Any\n+", "", source, flags=re.MULTILINE)


def ensure_field_import(source: str) -> str:
    """Ensure ``field`` is imported from dataclasses if ``field(`` is used."""
    if "field(" not in source:
        return source
    # Check if field is already imported
    if re.search(r"from dataclasses import.*\bfield\b", source):
        return source
    # Add field to existing dataclass import
    source = re.sub(
        r"from dataclasses import dataclass\b",
        "from dataclasses import dataclass, field",
        source,
    )
    return source


def clean_blank_lines(source: str) -> str:
    """Collapse runs of 3+ blank lines to 2 (Python convention)."""
    return re.sub(r"\n{4,}", "\n\n\n", source)


# ---------------------------------------------------------------------------
# Class name extraction
# ---------------------------------------------------------------------------


def extract_class_names(source: str) -> list[str]:
    """Extract all class and type alias names from Python source."""
    names: list[str] = []
    for line in source.split("\n"):
        # Class definition
        m = re.match(r"^class (\w+)", line)
        if m:
            names.append(m.group(1))
            continue
        # Type alias at module level
        m = re.match(r"^(\w+)\s*=\s*", line)
        if m and not line.startswith("    "):
            name = m.group(1)
            # Skip common non-class assignments
            if name not in ("Model",) and name[0].isupper():
                names.append(name)
    return names
