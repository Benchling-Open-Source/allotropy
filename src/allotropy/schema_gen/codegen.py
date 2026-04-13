"""Code generator: convert JSON Schema definitions to Python dataclass modules.

Generates one Python module per JSON schema file, with proper cross-module
imports based on $ref relationships.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import re
from typing import Any
import warnings

from allotropy.schema_gen.naming import (
    def_name_to_class_name,
    default_json_name,
    normalize_schema_url,
    parse_ref,
    property_name_to_class_name,
    property_name_to_python,
    quantity_value_class_name,
    schema_url_to_module_path,
    unit_symbol_to_class_name,
)


def _dquote(value: Any) -> str:
    """Format a value as a properly quoted Python literal string.

    Uses double quotes by default (ruff Q000). Falls back to single quotes
    when the value contains double quotes (ruff Q003).
    Non-string values fall back to repr().
    """
    if isinstance(value, str):
        if '"' in value:
            # Use single quotes to avoid escaping (Q003)
            escaped = value.replace("\\", "\\\\").replace("'", "\\'")
            return f"'{escaped}'"
        escaped = value.replace("\\", "\\\\")
        return f'"{escaped}"'
    return repr(value)


# Properties starting with these prefixes are schema metadata, not data fields
ASM_METADATA_PREFIXES = ("$asm.", "$schema", "$id", "$comment")

# JSON Schema validation keywords that refine a base-class field without
# defining a new type.  Schemas containing *only* these keys are "constraint-only
# overlays" and are skipped during property type resolution.
_CONSTRAINT_ONLY_KEYS = frozenset(
    {
        "required",
        "type",
        "minItems",
        "maxItems",
        "prefixItems",
        "contains",
        "minProperties",
        "maxProperties",
        "minimum",
        "maximum",
        "minLength",
        "maxLength",
        "pattern",
        "uniqueItems",
    }
)


# ---------------------------------------------------------------------------
# Intermediate Representation (IR)
# ---------------------------------------------------------------------------


@dataclass
class FieldDef:
    """A single field in a generated dataclass."""

    python_name: str
    type_str: str
    json_name: str
    is_required: bool


def _unit_field() -> FieldDef:
    """Create the standard ``unit: str`` field used in unit classes."""
    return FieldDef(
        python_name="unit", type_str="str", json_name="unit", is_required=True
    )


@dataclass
class ImportEntry:
    """A Python import to add to a generated module."""

    module: str  # Full module path (e.g., "allotropy.allotrope.models.adm.core...")
    name: str  # Class/type name to import
    reexport: bool = False  # If True, emit "import X as X" for mypy explicit re-export


@dataclass
class GeneratedClass:
    """A generated Python class, type alias, or enum.

    Exactly one of ``fields``, ``enum_members``, or ``alias_target`` is
    populated (the others stay ``None``).  A dataclass with no fields
    uses ``fields=[]`` (empty list, not None) to distinguish from aliases.
    """

    name: str
    # Dataclass fields (None = not a dataclass)
    fields: list[FieldDef] | None = None
    bases: list[str] = field(default_factory=list)
    frozen: bool = True
    # Enum members: list of (member_name, value)
    enum_members: list[tuple[str, str]] | None = None
    # Type alias target expression (e.g., "Foo | Bar")
    alias_target: str | None = None
    # Explicit set of type names this class depends on (for topological sort)
    dependencies: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        variants = [
            self.fields is not None,
            self.enum_members is not None,
            self.alias_target is not None,
        ]
        if sum(variants) > 1:
            msg = (
                f"GeneratedClass {self.name!r} has multiple variants set "
                f"(fields={self.fields is not None}, "
                f"enum_members={self.enum_members is not None}, "
                f"alias_target={self.alias_target is not None}). "
                f"Exactly one must be populated."
            )
            raise ValueError(msg)

    @property
    def is_type_alias(self) -> bool:
        return self.alias_target is not None

    def render(self) -> str:
        """Render this class as Python source code."""
        if self.alias_target is not None:
            return f"{self.name} = {self.alias_target}"

        if self.enum_members is not None:
            lines = [f"class {self.name}(Enum):"]
            for member_name, value in self.enum_members:
                lines.append(f"    {member_name} = {_dquote(value)}")
            return "\n".join(lines)

        # Dataclass
        frozen_str = "frozen=True, " if self.frozen else ""
        bases_str = f"({', '.join(self.bases)})" if self.bases else ""
        lines = [
            f"@dataclass({frozen_str}kw_only=True)",
            f"class {self.name}{bases_str}:",
        ]

        if not self.fields:
            lines.append("    pass")
        else:
            required = [f for f in self.fields if f.is_required]
            optional = [f for f in self.fields if not f.is_required]
            for f in required + optional:
                lines.append(
                    _field_declaration(
                        f.python_name,
                        f.type_str,
                        f.json_name,
                        is_required=f.is_required,
                    )
                )

        return "\n".join(lines)

    def copy(self) -> GeneratedClass:
        """Create a shallow copy suitable for mutation without affecting the original."""
        return GeneratedClass(
            name=self.name,
            fields=[
                FieldDef(
                    python_name=f.python_name,
                    type_str=f.type_str,
                    json_name=f.json_name,
                    is_required=f.is_required,
                )
                for f in self.fields
            ]
            if self.fields is not None
            else None,
            bases=list(self.bases),
            frozen=self.frozen,
            enum_members=list(self.enum_members)
            if self.enum_members is not None
            else None,
            alias_target=self.alias_target,
            dependencies=set(self.dependencies),
        )

    @property
    def needs_field_import(self) -> bool:
        """Whether this class uses the ``field()`` function from dataclasses."""
        if self.fields is None:
            return False
        return any(f.json_name != default_json_name(f.python_name) for f in self.fields)

    @property
    def needs_any_import(self) -> bool:
        """Whether this class references the ``Any`` type."""
        if self.alias_target is not None:
            return "Any" in self.alias_target
        if self.fields:
            return any("Any" in f.type_str for f in self.fields)
        return False

    @property
    def needs_literal_import(self) -> bool:
        """Whether this class references ``Literal[...]``."""
        if self.alias_target is not None:
            return "Literal[" in self.alias_target
        if self.fields:
            return any("Literal[" in f.type_str for f in self.fields)
        return False


def _extract_type_references(type_str: str) -> set[str]:
    """Extract potential class name references from a type expression.

    Returns names that start with an uppercase letter and could be
    locally-defined classes (for topological sort dependency tracking).
    """
    # Find all word-boundary identifiers starting with uppercase
    refs = set(re.findall(r"\b([A-Z]\w+)\b", type_str))
    # Exclude builtin/stdlib type names that are never local classes
    refs -= {"None", "Any", "Literal", "Enum"}
    return refs


@dataclass
class ModuleCode:
    """Complete generated code for a Python module."""

    schema_url: str
    imports: list[ImportEntry] = field(default_factory=list)
    classes: list[GeneratedClass] = field(default_factory=list)
    # Map from definition names in this schema to their Python class names
    exported_names: dict[str, str] = field(default_factory=dict)

    def render(self, models_package: str = "allotropy.allotrope.models") -> str:
        """Render the complete Python module source code.

        This method is pure — it does not mutate ``self.classes``.
        """
        # Deduplicate classes by name, merging fields from duplicates.
        # Multiple schema locations can generate the same inline type
        # (e.g., recursive PopulationDocumentItem) with slightly different
        # field sets — merge all fields so no properties are lost.
        seen_names: dict[str, int] = {}  # name -> index in unique
        unique: list[GeneratedClass] = []
        for cls in self.classes:
            if cls.name not in seen_names:
                seen_names[cls.name] = len(unique)
                unique.append(cls.copy())
            else:
                # Merge fields from the duplicate into the existing class
                existing = unique[seen_names[cls.name]]
                _merge_class_fields(existing, cls)

        # Reorder classes so that dependencies come before uses
        classes = _topological_sort_classes(unique)

        lines: list[str] = []
        lines.append("# generated by allotropy.schema_gen")
        lines.append("")
        lines.append("from __future__ import annotations")
        lines.append("")

        # Collect and deduplicate imports
        stdlib_imports: set[str] = set()
        external_imports: dict[str, set[str]] = defaultdict(set)

        # Check all generated classes for what imports are needed
        has_dataclasses = any(c.fields is not None for c in classes)
        if has_dataclasses:
            dc_names = ["dataclass"]
            if any(c.needs_field_import for c in classes):
                dc_names.append("field")
            stdlib_imports.add(f"from dataclasses import {', '.join(dc_names)}")
        if any(c.enum_members is not None for c in classes):
            stdlib_imports.add("from enum import Enum")
        typing_names: list[str] = []
        if any(c.needs_any_import for c in classes):
            typing_names.append("Any")
        if any(c.needs_literal_import for c in classes):
            typing_names.append("Literal")
        if typing_names:
            stdlib_imports.add(f"from typing import {', '.join(typing_names)}")

        # Names defined as local classes — imports of these would shadow or
        # be shadowed, producing F811 lint errors.
        local_class_names = {c.name for c in classes}

        # Track which names need explicit re-export (import X as X)
        reexport_names: set[str] = set()

        # Track already-imported names to avoid duplicate imports from
        # different modules (e.g. TQuantityValueX from both core re-export
        # and quantity_values).
        imported_names: set[str] = set()

        for imp in self.imports:
            if imp.name in local_class_names:
                continue
            if imp.name in imported_names:
                continue
            imported_names.add(imp.name)
            module = imp.module
            # Convert relative module path to full package path
            if not module.startswith("allotropy"):
                module = f"{models_package}.{module}"
            external_imports[module].add(imp.name)
            if imp.reexport:
                reexport_names.add(imp.name)

        # Write stdlib imports
        for stdlib_imp in sorted(stdlib_imports):
            lines.append(stdlib_imp)
        if stdlib_imports:
            lines.append("")

        # Write external imports
        for module in sorted(external_imports.keys()):
            names = sorted(external_imports[module])

            def _format_import_name(name: str) -> str:
                return f"{name} as {name}" if name in reexport_names else name

            if len(names) == 1:
                lines.append(f"from {module} import {_format_import_name(names[0])}")
            else:
                lines.append(f"from {module} import (")
                for name in names:
                    lines.append(f"    {_format_import_name(name)},")
                lines.append(")")
        if external_imports:
            lines.append("")
        lines.append("")

        # Write classes and type aliases
        for cls in classes:
            lines.append(cls.render())
            lines.append("")
            lines.append("")

        # Remove trailing blank lines
        while lines and lines[-1] == "":
            lines.pop()
        lines.append("")  # Single trailing newline

        return "\n".join(lines)


def _topological_sort_classes(classes: list[GeneratedClass]) -> list[GeneratedClass]:
    """Sort classes so that dependencies come before uses.

    Uses the explicit ``dependencies`` set on each class rather than
    regex-scanning code strings.
    """
    name_to_idx: dict[str, int] = {cls.name: i for i, cls in enumerate(classes)}
    local_names = set(name_to_idx.keys())

    # Build dependency graph: index -> set of indices it depends on
    deps: dict[int, set[int]] = {i: set() for i in range(len(classes))}
    for i, cls in enumerate(classes):
        for dep_name in cls.dependencies & local_names:
            if dep_name in name_to_idx and name_to_idx[dep_name] != i:
                deps[i].add(name_to_idx[dep_name])

    # Topological sort (Kahn's algorithm) with alphabetical tie-breaking
    # for deterministic output across runs.
    in_degree = {i: len(d) for i, d in deps.items()}
    queue: deque[int] = deque(
        sorted(
            [i for i, d in in_degree.items() if d == 0], key=lambda i: classes[i].name
        )
    )
    result: list[int] = []

    while queue:
        idx = queue.popleft()
        result.append(idx)
        newly_ready: list[int] = []
        for other, dep_set in deps.items():
            if idx in dep_set:
                in_degree[other] -= 1
                if in_degree[other] == 0:
                    newly_ready.append(other)
        queue.extend(sorted(newly_ready, key=lambda i: classes[i].name))

    # Handle cycles (shouldn't happen but be safe)
    if len(result) != len(classes):
        remaining = sorted(set(range(len(classes))) - set(result))
        result.extend(remaining)

    return [classes[i] for i in result]


def _merge_class_fields(existing: GeneratedClass, new: GeneratedClass) -> None:
    """Merge fields from *new* into *existing*, deduplicating by field name.

    Only operates on dataclasses (``fields is not None``).  Type aliases
    and enums are left unchanged.
    """
    if existing.fields is None or new.fields is None:
        return

    existing_names = {f.python_name for f in existing.fields}
    for f in new.fields:
        if f.python_name not in existing_names:
            existing.fields.append(f)
            existing_names.add(f.python_name)

    # Merge dependencies
    existing.dependencies |= new.dependencies


def _field_declaration(
    python_name: str, type_str: str, json_name: str, *, is_required: bool
) -> str:
    """Generate a dataclass field declaration, with JSON name metadata when needed.

    Omits json_name when the mapping is a straightforward space-to-underscore
    conversion. Only emits metadata for non-trivial name transformations.
    """
    needs_json_name = json_name != default_json_name(python_name)
    if needs_json_name:
        metadata = f'{{"json_name": {_dquote(json_name)}}}'
        if is_required:
            return f"    {python_name}: {type_str} = field(metadata={metadata})"
        return f"    {python_name}: {type_str} | None = field(default=None, metadata={metadata})"
    if is_required:
        return f"    {python_name}: {type_str}"
    return f"    {python_name}: {type_str} | None = None"


# ---------------------------------------------------------------------------
# Schema merging utilities (pure functions)
# ---------------------------------------------------------------------------


def _strip_required_recursive(schema: Any) -> Any:
    """Recursively remove all ``required`` arrays from a schema.

    Used after merging anyOf variants: in a union type, no individual
    variant's fields should be strictly required in the merged result,
    since only one variant applies at runtime.
    """
    if isinstance(schema, dict):
        return {
            k: _strip_required_recursive(v)
            for k, v in schema.items()
            if k != "required"
        }
    if isinstance(schema, list):
        return [_strip_required_recursive(item) for item in schema]
    return schema


def _absolutize_refs(schema: Any, base_url: str) -> Any:
    """Rewrite local ``#/$defs/...`` refs to absolute URLs.

    When properties from one schema file are deep-merged into a different
    schema's context, local refs become dangling.  This function rewrites
    them to ``{base_url}#/$defs/...`` so they resolve correctly.
    """
    if isinstance(schema, dict):
        result: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "$ref" and isinstance(value, str) and value.startswith("#/"):
                result[key] = f"{base_url}{value}"
            else:
                result[key] = _absolutize_refs(value, base_url)
        return result
    if isinstance(schema, list):
        return [_absolutize_refs(item, base_url) for item in schema]
    return schema


def _deep_merge_schemas(
    base: dict[str, Any],
    overlay: dict[str, Any],
    *,
    any_of: bool = False,
) -> dict[str, Any]:
    """Deep-merge two JSON schemas, with *overlay* taking precedence.

    Recursively merges ``properties`` dicts and ``items`` sub-schemas so that
    a technique schema overlay inherits all nested structure from the base
    hierarchy schema while adding or replacing its own fields.

    When *any_of* is True (merging anyOf variants), ``required`` arrays are
    intersected rather than unioned — a field is only required in the merged
    result if both variants require it.
    """
    result = dict(base)

    for key, value in overlay.items():
        if key == "properties" and "properties" in result:
            merged = dict(result["properties"])
            for pname, pschema in value.items():
                if (
                    pname in merged
                    and isinstance(merged[pname], dict)
                    and isinstance(pschema, dict)
                ):
                    merged[pname] = _deep_merge_schemas(
                        merged[pname], pschema, any_of=any_of
                    )
                else:
                    merged[pname] = pschema
            result["properties"] = merged
        elif key == "required":
            if "required" in result:
                if any_of:
                    result["required"] = list(set(result["required"]) & set(value))
                else:
                    result["required"] = list(set(result["required"]) | set(value))
            elif any_of:
                # anyOf: overlay has required but base doesn't →
                # intersection with ∅ = ∅, so don't add.
                pass
            else:
                result[key] = value
        elif key == "items" and "items" in result:
            if isinstance(result["items"], dict) and isinstance(value, dict):
                result["items"] = _deep_merge_schemas(
                    result["items"], value, any_of=any_of
                )
            else:
                result[key] = value
        elif key == "allOf" and "allOf" in result:
            if any_of:
                # In anyOf mode, merge inline allOf items with anyOf semantics
                # so that nested required fields get intersected rather than
                # accumulated.  $ref items are deduplicated.
                refs: set[str] = set()
                inline_items: list[dict[str, Any]] = []
                for item in result["allOf"] + value:
                    if "$ref" in item and len(item) == 1:
                        refs.add(item["$ref"])
                    elif isinstance(item, dict):
                        inline_items.append(item)
                merged_inline: dict[str, Any] = {}
                for item in inline_items:
                    if merged_inline:
                        merged_inline = _deep_merge_schemas(
                            merged_inline, item, any_of=True
                        )
                    else:
                        merged_inline = dict(item)
                result_allof: list[dict[str, Any]] = [{"$ref": r} for r in refs]
                if merged_inline:
                    result_allof.append(merged_inline)
                result["allOf"] = result_allof
            else:
                result["allOf"] = result["allOf"] + value
        else:
            result[key] = value

    # In anyOf mode: if the base had "required" but the overlay didn't
    # define any, the intersection with ∅ is ∅.
    if any_of and "required" in result and "required" not in overlay:
        result["required"] = []

    return result


# ---------------------------------------------------------------------------
# Shared definition types and modules
# ---------------------------------------------------------------------------

# These base types are defined once in shared/definitions/definitions.py and
# imported into each generated core module rather than being regenerated per
# core version.  This lets utilities like quantity_or_none() accept any
# TQuantityValue subclass regardless of which core version produced it.
# The imports use "import X as X" so mypy treats them as explicit re-exports,
# allowing downstream generated modules to import them from core.py.
_SHARED_DEFINITION_TYPES: dict[str, str] = {
    "tQuantityValue": "TQuantityValue",
    "tStatisticDatumRole": "TStatisticDatumRole",
    "tClass": "TClass",
    "tUnit": "TUnit",
}

_SHARED_DEFINITIONS_MODULE = "allotropy.allotrope.models.shared.definitions.definitions"

# Shared module where TQuantityValue{Unit} thin subclasses live.
# The codegen imports from here rather than generating subclasses in each
# core.py.  When a schema introduces a unit not yet in this module, the
# codegen records it and generate.py appends the new class.
_SHARED_QUANTITY_VALUES_MODULE = (
    "allotropy.allotrope.models.shared.definitions.quantity_values"
)


# ---------------------------------------------------------------------------
# Schema merging helper
# ---------------------------------------------------------------------------


class SchemaMerger:
    """Merges properties from variant sub-schemas (anyOf/oneOf composition).

    Extracted from SchemaCodeGenerator so the merge logic can be tested
    and reasoned about independently of code generation.
    """

    def __init__(self, schemas: dict[str, dict[str, Any]]) -> None:
        self.schemas = schemas

    def resolve_ref_to_schema(
        self, current_schema_url: str, ref: str
    ) -> dict[str, Any] | None:
        """Resolve a $ref string to its actual JSON Schema definition dict."""
        ref_schema_url, def_name = parse_ref(ref)

        if ref_schema_url is None:
            schema = self.schemas.get(current_schema_url, {})
            if def_name:
                defs: dict[str, Any] = schema.get("$defs", {})
                return defs.get(def_name)
            return None

        schema = self.schemas.get(ref_schema_url, {})
        if def_name:
            defs = schema.get("$defs", {})
            return defs.get(def_name)
        return schema

    def deep_merge_base_ref_properties(
        self,
        schema_url: str,
        base_refs: list[str],
        merged_props: dict[str, Any],
    ) -> None:
        """Deep-merge overlapping properties from base $ref schemas into merged_props.

        When a technique schema extends a base (e.g., techniqueAggregateDocument)
        and redefines a nested property (e.g., "device system document"), the
        base's full schema must be merged in so that inline types include all
        hierarchy-level fields plus technique-specific additions.
        """
        for ref in base_refs:
            ref_base_url = ref.split("#")[0]
            base_schema = self.resolve_ref_to_schema(schema_url, ref)
            if base_schema and "properties" in base_schema:
                base_props = base_schema["properties"]
                if ref_base_url:
                    base_props = {
                        k: _absolutize_refs(v, ref_base_url)
                        for k, v in base_props.items()
                    }
                for prop_key in list(merged_props.keys()):
                    if prop_key in base_props:
                        merged_props[prop_key] = _deep_merge_schemas(
                            base_props[prop_key], merged_props[prop_key]
                        )

    def merge_variant_properties(
        self,
        schema_url: str,
        variants: list[dict[str, Any]],
        merged_props: dict[str, Any],
    ) -> None:
        """Merge properties from anyOf/oneOf variant sub-schemas.

        Resolves each variant's ``$ref`` to its schema definition and
        deep-merges its properties into *merged_props*.  Also recurses
        one level into nested anyOf/oneOf within each variant (e.g.,
        detector sub-schemas that have oneOf for data cube types).
        """
        for variant in variants:
            variant_schema: dict[str, Any] | None = None
            variant_base_url = ""
            if "$ref" in variant:
                variant_base_url = variant["$ref"].split("#")[0]
                variant_schema = self.resolve_ref_to_schema(schema_url, variant["$ref"])
            elif isinstance(variant, dict):
                variant_schema = variant
            if not variant_schema:
                continue
            if "properties" in variant_schema:
                vprops = variant_schema["properties"]
                if variant_base_url:
                    vprops = {
                        k: _absolutize_refs(v, variant_base_url)
                        for k, v in vprops.items()
                    }
                for pk, pv in vprops.items():
                    if pk in merged_props:
                        merged_props[pk] = _deep_merge_schemas(merged_props[pk], pv)
                    else:
                        merged_props[pk] = pv
            # Recurse one level into nested anyOf/oneOf within the variant
            # (e.g., a detector sub-schema has oneOf for different data cubes).
            # Only one level is supported — deeper nesting raises a warning.
            for nested_key in ("anyOf", "oneOf"):
                if nested_key in variant_schema:
                    for nested in variant_schema[nested_key]:
                        nested_schema: dict[str, Any] | None = None
                        nested_base_url = variant_base_url
                        if "$ref" in nested:
                            nested_base_url = (
                                nested["$ref"].split("#")[0] or variant_base_url
                            )
                            nested_schema = self.resolve_ref_to_schema(
                                schema_url, nested["$ref"]
                            )
                        elif isinstance(nested, dict) and "properties" in nested:
                            nested_schema = nested
                        if nested_schema and "properties" in nested_schema:
                            nprops = nested_schema["properties"]
                            if nested_base_url:
                                nprops = {
                                    k: _absolutize_refs(v, nested_base_url)
                                    for k, v in nprops.items()
                                }
                            for pk, pv in nprops.items():
                                if pk in merged_props:
                                    merged_props[pk] = _deep_merge_schemas(
                                        merged_props[pk], pv
                                    )
                                else:
                                    merged_props[pk] = pv
                        # Warn if this nested schema itself has further
                        # anyOf/oneOf — those properties would be silently
                        # dropped since we only recurse one level.
                        if nested_schema:
                            for deeper_key in ("anyOf", "oneOf"):
                                if deeper_key in nested_schema:
                                    warnings.warn(
                                        f"Schema {schema_url} has 3+ levels of "
                                        f"anyOf/oneOf nesting ({deeper_key} inside "
                                        f"{nested_key}). Properties from the "
                                        f"innermost level are not merged.",
                                        stacklevel=2,
                                    )

    def merge_any_of_variants_into_props(
        self,
        schema_url: str,
        any_of_variants: list[dict[str, Any]],
        merged_props: dict[str, Any],
    ) -> None:
        """Merge anyOf variant schemas into merged_props as optional fields.

        Resolves each variant's ``$ref``, deep-merges all variants together
        with ``any_of=True`` (intersecting required arrays), strips all
        ``required`` from the result, and folds the resulting properties
        into *merged_props*.  Also collects nested ``oneOf`` variants from
        each resolved schema and merges those properties too.

        This handles the multi-detector pattern where anyOf variants each
        contribute different measurement fields to a common item type.
        """
        any_of_merged: dict[str, Any] | None = None
        # Collect all oneOf variants from all detector schemas before
        # deep-merge (which overwrites oneOf with the last value).
        all_one_of_variants: list[dict[str, Any]] = []

        for variant in any_of_variants:
            if "$ref" in variant:
                ref_schema_url, ref_def = parse_ref(variant["$ref"])
                if ref_def:
                    if ref_schema_url:
                        ref_schema = self.schemas.get(ref_schema_url, {})
                    else:
                        ref_schema = self.schemas.get(schema_url, {})
                    ref_def_schema = ref_schema.get("$defs", {}).get(ref_def, {})
                    # Collect oneOf variants before deep-merge
                    abs_base = ref_schema_url or schema_url
                    if "oneOf" in ref_def_schema:
                        for one_of_v in ref_def_schema["oneOf"]:
                            all_one_of_variants.append(
                                _absolutize_refs(one_of_v, abs_base)
                            )
                    if any_of_merged is None:
                        any_of_merged = dict(ref_def_schema)
                    else:
                        any_of_merged = _deep_merge_schemas(
                            any_of_merged, ref_def_schema, any_of=True
                        )
            elif isinstance(variant, dict) and "properties" in variant:
                if any_of_merged is None:
                    any_of_merged = dict(variant)
                else:
                    any_of_merged = _deep_merge_schemas(
                        any_of_merged, variant, any_of=True
                    )

        if any_of_merged:
            # Strip all required arrays: in a union, no variant's fields
            # should be strictly required since only one variant applies.
            any_of_stripped: dict[str, Any] = _strip_required_recursive(any_of_merged)
            if "properties" in any_of_stripped:
                for pk, pv in any_of_stripped["properties"].items():
                    if pk in merged_props:
                        merged_props[pk] = _deep_merge_schemas(
                            merged_props[pk], pv, any_of=True
                        )
                    else:
                        merged_props[pk] = pv

        # Extract properties from oneOf variants as optional fields
        for one_of_v in all_one_of_variants:
            if isinstance(one_of_v, dict) and "properties" in one_of_v:
                for pk, pv in one_of_v["properties"].items():
                    if pk not in merged_props:
                        merged_props[pk] = pv
                    else:
                        merged_props[pk] = _deep_merge_schemas(
                            merged_props[pk], pv, any_of=True
                        )


# ---------------------------------------------------------------------------
# Quantity value manager
# ---------------------------------------------------------------------------


class QuantityValueManager:
    """Tracks and manages TQuantityValue{Unit} thin subclasses.

    Centralizes the logic for resolving quantity value types, checking
    whether they already exist in the shared module, and recording new
    ones that need to be appended.
    """

    def __init__(
        self,
        existing_classes: set[str] | None = None,
    ) -> None:
        self._known: set[str] = existing_classes or set()
        self.new_classes: list[tuple[str, str]] = []

    def get_or_create(self, unit_const: str) -> str:
        """Return the class name for *unit_const*, recording it as new if needed."""
        class_name = quantity_value_class_name(unit_const)
        if class_name not in self._known:
            self._known.add(class_name)
            self.new_classes.append((class_name, unit_const))
        return class_name


# ---------------------------------------------------------------------------
# Main code generator
# ---------------------------------------------------------------------------


class SchemaCodeGenerator:
    """Generates Python code from a set of JSON schemas."""

    def __init__(
        self,
        schemas: dict[str, dict[str, Any]],
        generation_order: list[str],
        models_package: str = "allotropy.allotrope.models",
        existing_quantity_value_classes: set[str] | None = None,
    ) -> None:
        self.schemas = schemas
        self.generation_order = generation_order
        self.models_package = models_package
        # Track generated modules for cross-references
        self._modules: dict[str, ModuleCode] = {}
        # Track unit symbols and their const values for quantity value generation
        self._unit_symbols: dict[str, str] = {}  # def_name -> const_value
        # Schema merging helper
        self._merger = SchemaMerger(schemas)
        # Quantity value lifecycle manager
        self._qv_manager = QuantityValueManager(existing_quantity_value_classes)

    @property
    def new_quantity_value_classes(self) -> list[tuple[str, str]]:
        return self._qv_manager.new_classes

    def generate_all(self) -> dict[str, ModuleCode]:
        """Generate Python modules for all schemas in dependency order."""
        for url in self.generation_order:
            schema = self.schemas[url]
            module = self._generate_module(url, schema)
            self._modules[url] = module
        return self._modules

    def _generate_module(self, schema_url: str, schema: dict[str, Any]) -> ModuleCode:
        """Generate a Python module for a single schema."""
        module = ModuleCode(schema_url=schema_url)

        defs = schema.get("$defs", {})

        if self._is_units_schema(schema_url):
            self._generate_units_module(module, defs)
        else:
            # Generate $defs classes if present (core, hierarchy, detector types, etc.)
            if defs:
                self._generate_defs_module(module, schema_url, defs)
            # Generate ADM top-level Model class if this is a technique schema
            if self._is_adm_schema(schema):
                self._generate_adm_module(module, schema_url, schema)

        return module

    def _is_units_schema(self, url: str) -> bool:
        return "units.schema" in url

    @staticmethod
    def _is_adm_schema(schema: dict[str, Any]) -> bool:
        """Check if this is a top-level ADM schema (has allOf at root)."""
        return "allOf" in schema

    # -------------------------------------------------------------------------
    # Units schema generation
    # -------------------------------------------------------------------------

    def _generate_units_module(self, module: ModuleCode, defs: dict[str, Any]) -> None:
        """Generate the units module with a HasUnit base class and unit subclasses."""
        module.classes.append(GeneratedClass(name="HasUnit", fields=[_unit_field()]))
        module.exported_names["HasUnit"] = "HasUnit"

        used_class_names: set[str] = {"HasUnit"}
        for def_name, def_schema in defs.items():
            const_value = self._extract_unit_const(def_schema)
            if const_value is None:
                continue
            class_name = unit_symbol_to_class_name(const_value)
            self._unit_symbols[def_name] = const_value

            # Deduplicate class names with a numeric suffix
            base_name = class_name
            counter = 2
            while class_name in used_class_names:
                class_name = f"{base_name}{counter}"
                counter += 1
            used_class_names.add(class_name)

            module.classes.append(
                GeneratedClass(
                    name=class_name,
                    fields=[_unit_field()],
                    bases=["HasUnit"],
                    dependencies={"HasUnit"},
                )
            )
            module.exported_names[def_name] = class_name

    @staticmethod
    def _extract_unit_const(schema: dict[str, Any]) -> str | None:
        """Extract the const unit value from a unit definition."""
        props = schema.get("properties", {})
        unit_prop = props.get("unit", {})
        const: str | None = unit_prop.get("const")
        return const

    # -------------------------------------------------------------------------
    # Regular $defs module generation (core, cube, hierarchy, manifest, detector)
    # -------------------------------------------------------------------------

    def _generate_defs_module(
        self, module: ModuleCode, schema_url: str, defs: dict[str, Any]
    ) -> None:
        """Generate classes for all $defs in a schema."""
        is_core = False
        for def_name, def_schema in defs.items():
            if not isinstance(def_schema, dict):
                continue

            # Import shared definition types instead of regenerating them.
            # Re-exported here so downstream generated modules can import
            # from this core module without needing to know the source.
            if def_name in _SHARED_DEFINITION_TYPES:
                class_name = _SHARED_DEFINITION_TYPES[def_name]
                module.imports.append(
                    ImportEntry(
                        module=_SHARED_DEFINITIONS_MODULE,
                        name=class_name,
                        reexport=True,
                    )
                )
                module.exported_names[def_name] = class_name
                is_core = True
                continue

            class_name = def_name_to_class_name(def_name)
            cls = self._generate_type(module, schema_url, class_name, def_schema)
            if cls:
                module.classes.append(cls)
                module.exported_names[def_name] = class_name

        # Core modules re-export ALL existing TQuantityValue{Unit} classes
        # so that schema mappers can import them from core.py.  This set is
        # deterministic (every class in quantity_values.py), making core.py
        # output identical regardless of which technique schemas are processed.
        if is_core:
            for qv_class in sorted(self._qv_manager._known):
                if not any(
                    imp.name == qv_class
                    and imp.module == _SHARED_QUANTITY_VALUES_MODULE
                    for imp in module.imports
                ):
                    module.imports.append(
                        ImportEntry(
                            module=_SHARED_QUANTITY_VALUES_MODULE,
                            name=qv_class,
                            reexport=True,
                        )
                    )
                    module.exported_names[qv_class] = qv_class

    def _generate_type(
        self,
        module: ModuleCode,
        schema_url: str,
        class_name: str,
        schema: dict[str, Any],
    ) -> GeneratedClass | None:
        """Generate a Python class or type alias for a single type definition."""
        # Handle oneOf patterns (value types like tStringValue)
        if "oneOf" in schema:
            return self._generate_one_of(module, schema_url, class_name, schema)

        # Handle anyOf patterns (union types like tNumericValue, tOrderedValue)
        if "anyOf" in schema:
            return self._generate_any_of(module, schema_url, class_name, schema)

        # Handle enum types
        if "enum" in schema:
            return self._generate_enum(class_name, schema)

        # Handle object types with properties
        if schema.get("type") == "object" and "properties" in schema:
            return self._generate_dataclass(module, schema_url, class_name, schema)

        # Handle object type without properties (just a marker/base type)
        if schema.get("type") == "object":
            return GeneratedClass(name=class_name, fields=[])

        # Handle array type aliases with typed items (e.g., tNumberArray)
        if schema.get("type") == "array" and "items" in schema:
            items = schema["items"]
            if "allOf" in items:
                item_type = self._resolve_all_of_array_items(
                    module, schema_url, class_name, items
                )
                return _make_alias(class_name, f"list[{item_type}]")
            item_type = self._resolve_array_item_type(module, schema_url, items)
            return _make_alias(class_name, f"list[{item_type}]")

        # Handle simple type aliases
        if "type" in schema:
            python_type = self._json_type_to_python(schema["type"])
            return _make_alias(class_name, python_type)

        # Handle allOf at the definition level
        if "allOf" in schema:
            return self._generate_all_of_def(module, schema_url, class_name, schema)

        # Handle $ref at the top level of a def (alias)
        if "$ref" in schema:
            ref_type = self._resolve_ref_type(module, schema_url, schema["$ref"])
            return _make_alias(class_name, ref_type)

        # Handle dependencies/constraints (like tRangeValue)
        if "properties" in schema:
            return self._generate_dataclass(module, schema_url, class_name, schema)

        warnings.warn(
            f"Unrecognized schema pattern for {class_name!r} in {schema_url}, "
            f"skipping. Keys: {sorted(schema.keys())}",
            stacklevel=2,
        )
        return None

    # -------------------------------------------------------------------------
    # oneOf: value types (primitive | typed object)
    # -------------------------------------------------------------------------

    def _generate_one_of(
        self,
        module: ModuleCode,
        schema_url: str,
        class_name: str,
        schema: dict[str, Any],
    ) -> GeneratedClass:
        """Generate a type for a oneOf schema.

        Common pattern: oneOf[primitive_type, {type: object, properties: {value, @type}}]
        → Generate both the typed object class and a union alias.
        """
        one_of = schema["oneOf"]

        # Check for the common "primitive | typed object" pattern
        primitive_types: list[str] = []
        object_schemas: list[dict[str, Any]] = []
        ref_types: list[str] = []

        for variant in one_of:
            if "$ref" in variant:
                ref_type = self._resolve_ref_type(module, schema_url, variant["$ref"])
                ref_types.append(ref_type)
            elif "properties" in variant:
                object_schemas.append(variant)
            elif "type" in variant:
                python_type = self._json_type_to_python(variant["type"])
                primitive_types.append(python_type)
            elif "format" in variant:
                primitive_types.append("str")
            elif set(variant.keys()) <= {"required"}:
                pass  # Skip constraint-only variants

        parts: list[str] = []

        # If there's a primitive + object variant, generate a typed item class
        if primitive_types and object_schemas:
            item_class_name = f"{class_name}Item"
            item_cls = self._generate_dataclass(
                module, schema_url, item_class_name, object_schemas[0]
            )
            if item_cls:
                module.classes.append(item_cls)
                module.exported_names[f"{class_name}_item"] = item_class_name
            parts.extend(primitive_types)
            parts.append(item_class_name)
        elif primitive_types:
            parts.extend(primitive_types)
        elif object_schemas:
            if len(object_schemas) == 1:
                return self._generate_dataclass(
                    module, schema_url, class_name, object_schemas[0]
                )
            # Multiple object variants — merge all properties
            merged_props: dict[str, Any] = {}
            for obj_schema in object_schemas:
                merged_props.update(obj_schema.get("properties", {}))
            merged = {"type": "object", "properties": merged_props}
            return self._generate_dataclass(module, schema_url, class_name, merged)

        # Add ref types
        parts.extend(ref_types)

        if not parts:
            return _make_alias(class_name, "Any")
        if len(parts) == 1:
            return _make_alias(class_name, parts[0])
        return _make_alias(class_name, _join_union(parts))

    # -------------------------------------------------------------------------
    # anyOf: union types
    # -------------------------------------------------------------------------

    def _generate_any_of(
        self,
        module: ModuleCode,
        schema_url: str,
        class_name: str,
        schema: dict[str, Any],
    ) -> GeneratedClass:
        """Generate a Union type alias for an anyOf schema."""
        any_of = schema["anyOf"]
        parts: list[str] = []
        for variant in any_of:
            if "$ref" in variant:
                ref_type = self._resolve_ref_type(module, schema_url, variant["$ref"])
                parts.append(ref_type)
            elif "type" in variant:
                parts.append(self._json_type_to_python(variant["type"]))

        if len(parts) == 1:
            return _make_alias(class_name, parts[0])
        return _make_alias(class_name, _join_union(parts))

    # -------------------------------------------------------------------------
    # enum types
    # -------------------------------------------------------------------------

    def _generate_enum(self, class_name: str, schema: dict[str, Any]) -> GeneratedClass:
        """Generate an Enum class for an enum schema."""
        values = schema["enum"]
        members = [(property_name_to_python(str(v)), str(v)) for v in values]
        return GeneratedClass(name=class_name, enum_members=members)

    # -------------------------------------------------------------------------
    # allOf at definition level
    # -------------------------------------------------------------------------

    def _generate_all_of_def(
        self,
        module: ModuleCode,
        schema_url: str,
        class_name: str,
        schema: dict[str, Any],
    ) -> GeneratedClass:
        """Generate a type for an allOf at the definition level."""
        all_of = schema["allOf"]
        merged_props: dict[str, Any] = {}
        merged_required: list[str] = []
        base_classes: list[str] = []

        for item in all_of:
            if "$ref" in item:
                ref_type = self._resolve_ref_type(module, schema_url, item["$ref"])
                base_classes.append(ref_type)
            if "properties" in item:
                merged_props.update(item["properties"])
            if "required" in item:
                merged_required.extend(item["required"])
            if isinstance(item, dict):
                for variant_key in ("anyOf", "oneOf"):
                    if variant_key in item:
                        self._merger.merge_variant_properties(
                            schema_url, item[variant_key], merged_props
                        )

        if not merged_props and base_classes:
            return GeneratedClass(
                name=class_name,
                fields=[],
                bases=base_classes,
                dependencies=set(base_classes),
            )

        merged = {"type": "object", "properties": merged_props}
        if merged_required:
            merged["required"] = merged_required
        return self._generate_dataclass(
            module, schema_url, class_name, merged, base_classes=base_classes
        )

    # -------------------------------------------------------------------------
    # Object → dataclass generation
    # -------------------------------------------------------------------------

    def _generate_dataclass(
        self,
        module: ModuleCode,
        schema_url: str,
        class_name: str,
        schema: dict[str, Any],
        *,
        base_classes: list[str] | None = None,
        frozen: bool = True,
    ) -> GeneratedClass:
        """Generate a frozen dataclass from an object schema."""
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        fields_list: list[FieldDef] = []
        deps: set[str] = set(base_classes) if base_classes else set()

        for prop_name, prop_schema in properties.items():
            if any(prop_name.startswith(p) for p in ASM_METADATA_PREFIXES):
                continue

            python_name = property_name_to_python(prop_name)
            type_str = self._resolve_property_type(
                module, schema_url, prop_name, prop_schema
            )
            # None means constraint-only overlay — skip
            if type_str is None:
                continue
            is_required = prop_name in required
            fields_list.append(
                FieldDef(
                    python_name=python_name,
                    type_str=type_str,
                    json_name=prop_name,
                    is_required=is_required,
                )
            )
            deps |= _extract_type_references(type_str)

        return GeneratedClass(
            name=class_name,
            fields=fields_list,
            bases=list(base_classes) if base_classes else [],
            frozen=frozen,
            dependencies=deps,
        )

    # -------------------------------------------------------------------------
    # Property type resolution
    # -------------------------------------------------------------------------

    def _resolve_property_type(
        self,
        module: ModuleCode,
        schema_url: str,
        prop_name: str,
        prop_schema: dict[str, Any],
    ) -> str | None:
        """Determine the Python type for a property schema."""
        # Strip $asm metadata from the schema copy
        prop_schema = {
            k: v
            for k, v in prop_schema.items()
            if not any(k.startswith(p) for p in ASM_METADATA_PREFIXES)
        }

        # $ref (with or without additional constraints like required/minItems)
        if "$ref" in prop_schema:
            return self._resolve_ref_type(module, schema_url, prop_schema["$ref"])

        # allOf pattern - check for quantity value + unit
        if "allOf" in prop_schema:
            return self._resolve_all_of_property(
                module, schema_url, prop_name, prop_schema
            )

        # anyOf - check for detector measurement items pattern
        if "anyOf" in prop_schema:
            return self._resolve_any_of_property(module, schema_url, prop_schema)

        # oneOf with properties: oneOf is just validation constraints, generate from properties
        if "oneOf" in prop_schema and "properties" in prop_schema:
            inline_class_name = property_name_to_class_name(prop_name)
            cls = self._generate_dataclass(
                module, schema_url, inline_class_name, prop_schema
            )
            module.classes.append(cls)
            return inline_class_name

        # oneOf
        if "oneOf" in prop_schema:
            return self._resolve_one_of_property(
                module, schema_url, prop_name, prop_schema
            )

        # Array type (explicit or implicit via items key)
        if prop_schema.get("type") == "array" or (
            "items" in prop_schema and "properties" not in prop_schema
        ):
            return self._resolve_array_type(module, schema_url, prop_name, prop_schema)

        # Inline object (with or without explicit type: "object")
        if "properties" in prop_schema:
            inline_class_name = property_name_to_class_name(prop_name)
            cls = self._generate_dataclass(
                module, schema_url, inline_class_name, prop_schema
            )
            # If all inner properties were constraint-only, the class is empty —
            # this means the whole property is a constraint overlay, skip it.
            if not cls.fields:
                return None
            module.classes.append(cls)
            return inline_class_name

        # Enum/const — generate a named Enum class so parsers can use members
        if "enum" in prop_schema:
            values = prop_schema["enum"]
            if len(values) > 1:
                enum_class_name = property_name_to_class_name(prop_name)
                cls = self._generate_enum(enum_class_name, prop_schema)
                module.classes.append(cls)
                return enum_class_name
            literals = ", ".join(_dquote(v) for v in values)
            return f"Literal[{literals}]"
        if "const" in prop_schema:
            return f"Literal[{_dquote(prop_schema['const'])}]"

        # Simple types
        if "type" in prop_schema:
            return self._json_type_to_python(prop_schema["type"])

        # Format-based type
        if "format" in prop_schema:
            return "str"

        # Constraint-only overlays refine a base-class field, not define new types.
        # An empty schema (all keys were $asm metadata) is a real field typed as Any.
        if prop_schema and prop_schema.keys() <= _CONSTRAINT_ONLY_KEYS:
            return None

        if prop_schema:
            warnings.warn(
                f"Unrecognized property schema for {prop_name!r} in {schema_url}, "
                f"falling back to Any. Keys: {sorted(prop_schema.keys())}",
                stacklevel=2,
            )
        return "Any"

    # -------------------------------------------------------------------------
    # allOf property resolution — decomposed into pattern matchers
    # -------------------------------------------------------------------------

    def _resolve_all_of_property(
        self,
        module: ModuleCode,
        schema_url: str,
        prop_name: str,
        prop_schema: dict[str, Any],
    ) -> str:
        """Resolve an allOf property type by trying each pattern in priority order."""
        all_of = prop_schema["allOf"]
        refs, inline_schemas = _partition_all_of(all_of)

        # Pattern 1: tQuantityValue + unit ref(s) → TQuantityValue{Unit}
        result = self._try_quantity_value_pattern(
            module, schema_url, refs, inline_schemas
        )
        if result:
            return result

        # Pattern 2: tClass + enum → Enum class or Literal
        result = self._try_class_enum_pattern(module, prop_name, refs, inline_schemas)
        if result:
            return result

        # Pattern 3/4: Merge allOf into an inline class
        return self._resolve_all_of_merged_class(
            module, schema_url, prop_name, prop_schema, all_of, refs
        )

    def _try_quantity_value_pattern(
        self,
        module: ModuleCode,
        schema_url: str,
        refs: list[str],
        inline_schemas: list[dict[str, Any]],
    ) -> str | None:
        """Match allOf[tQuantityValue, unit_ref(s)] → TQuantityValue{Unit}.

        Also handles the oneOf-units variant:
        allOf[tQuantityValue, {oneOf: [unit1, unit2, ...]}]
        """
        quantity_ref = None
        unit_refs: list[str] = []
        for ref in refs:
            _, def_name = parse_ref(ref)
            if def_name and def_name.lower() == "tquantityvalue":
                quantity_ref = ref
            elif def_name:
                ref_schema_url = ref.split("#")[0]
                try:
                    canonical = (
                        normalize_schema_url(ref_schema_url) if ref_schema_url else None
                    )
                except ValueError:
                    canonical = None
                if canonical and "units.schema" in canonical:
                    unit_refs.append(ref)

        if not quantity_ref:
            return None

        # Single unit ref
        if len(unit_refs) == 1:
            return self._generate_quantity_value_type(
                module, schema_url, quantity_ref, unit_refs[0]
            )

        # Multiple unit refs
        if len(unit_refs) > 1:
            types = [
                self._generate_quantity_value_type(
                    module, schema_url, quantity_ref, uref
                )
                for uref in unit_refs
            ]
            seen: set[str] = set()
            unique_types: list[str] = []
            for t in types:
                if t not in seen:
                    seen.add(t)
                    unique_types.append(t)
            return _join_union(unique_types)

        # No direct unit refs — check for oneOf[unit1, unit2, ...] in inline schemas
        return self._try_quantity_value_one_of_units(
            module, schema_url, quantity_ref, inline_schemas
        )

    def _try_quantity_value_one_of_units(
        self,
        module: ModuleCode,
        schema_url: str,
        quantity_ref: str,
        inline_schemas: list[dict[str, Any]],
    ) -> str | None:
        """Match allOf[tQuantityValue, {oneOf: [unit1, unit2, ...]}]."""
        for s in inline_schemas:
            if "oneOf" not in s:
                continue
            one_of_unit_refs: list[str] = []
            for variant in s["oneOf"]:
                if "$ref" in variant:
                    ref_url = variant["$ref"].split("#")[0]
                    try:
                        canonical = normalize_schema_url(ref_url) if ref_url else None
                    except ValueError:
                        canonical = None
                    if canonical and "units.schema" in canonical:
                        one_of_unit_refs.append(variant["$ref"])
            if one_of_unit_refs:
                types = [
                    self._generate_quantity_value_type(
                        module, schema_url, quantity_ref, uref
                    )
                    for uref in one_of_unit_refs
                ]
                seen: set[str] = set()
                unique_types: list[str] = []
                for t in types:
                    if t not in seen:
                        seen.add(t)
                        unique_types.append(t)
                return _join_union(unique_types)
        return None

    def _try_class_enum_pattern(
        self,
        module: ModuleCode,
        prop_name: str,
        refs: list[str],
        inline_schemas: list[dict[str, Any]],
    ) -> str | None:
        """Match allOf[tClass, {enum: [...]}] → Enum class or Literal."""
        class_ref = None
        enum_values = None
        for ref in refs:
            _, def_name = parse_ref(ref)
            if def_name and def_name == "tClass":
                class_ref = ref
        for s in inline_schemas:
            if "enum" in s:
                enum_values = s["enum"]

        if not class_ref or enum_values is None:
            return None

        if len(enum_values) > 1:
            enum_class_name = property_name_to_class_name(prop_name)
            cls = self._generate_enum(enum_class_name, {"enum": enum_values})
            module.classes.append(cls)
            return enum_class_name

        literals = ", ".join(_dquote(v) for v in enum_values)
        return f"Literal[{literals}]"

    def _resolve_all_of_merged_class(
        self,
        module: ModuleCode,
        schema_url: str,
        prop_name: str,
        prop_schema: dict[str, Any],
        all_of: list[dict[str, Any]],
        refs: list[str],
    ) -> str:
        """Merge allOf items into an inline class (patterns 3 and 4)."""
        merged_props: dict[str, Any] = {}
        merged_required: list[str] = []
        base_refs: list[str] = []

        # Include properties from the schema itself (may exist after deep-merge
        # places both "allOf" and "properties" at the same level).
        if "properties" in prop_schema:
            for pk, pv in prop_schema["properties"].items():
                if pk in merged_props:
                    merged_props[pk] = _deep_merge_schemas(merged_props[pk], pv)
                else:
                    merged_props[pk] = pv
        if "required" in prop_schema:
            merged_required.extend(prop_schema["required"])

        for item in all_of:
            if "$ref" in item:
                base_refs.append(item["$ref"])
            if isinstance(item, dict):
                if "properties" in item:
                    for pk, pv in item["properties"].items():
                        if pk in merged_props:
                            merged_props[pk] = _deep_merge_schemas(merged_props[pk], pv)
                        else:
                            merged_props[pk] = pv
                if "required" in item:
                    merged_required.extend(item["required"])
                for variant_key in ("anyOf", "oneOf"):
                    if variant_key in item:
                        self._merger.merge_variant_properties(
                            schema_url, item[variant_key], merged_props
                        )

        if merged_props:
            inline_class_name = property_name_to_class_name(prop_name)
            base_classes: list[str] = []
            for ref in base_refs:
                ref_type = self._resolve_ref_type(module, schema_url, ref)
                # When the ref target's class name matches the inline class
                # name (e.g., both property_name_to_class_name("measurement
                # document") and def_name_to_class_name("measurementDocument")
                # produce "MeasurementDocument"), we can't use it as a base
                # class — that would be self-referencing.  Instead, inline
                # the ref's properties into the merged set.  Note: this
                # coupling between the two naming functions is intentional.
                if ref_type == inline_class_name:
                    ref_base_url = ref.split("#")[0]
                    ref_schema = self._merger.resolve_ref_to_schema(schema_url, ref)
                    if ref_schema and "properties" in ref_schema:
                        ref_props = ref_schema["properties"]
                        if ref_base_url:
                            ref_props = {
                                k: _absolutize_refs(v, ref_base_url)
                                for k, v in ref_props.items()
                            }
                        for pk, pv in ref_props.items():
                            if pk in merged_props:
                                merged_props[pk] = _deep_merge_schemas(
                                    pv, merged_props[pk]
                                )
                            else:
                                merged_props[pk] = pv
                    if ref_schema and "required" in ref_schema:
                        merged_required.extend(ref_schema["required"])
                else:
                    base_classes.append(ref_type)
            self._merger.deep_merge_base_ref_properties(
                schema_url, base_refs, merged_props
            )
            merged = {"type": "object", "properties": merged_props}
            if merged_required:
                merged["required"] = list(set(merged_required))
            cls = self._generate_dataclass(
                module, schema_url, inline_class_name, merged, base_classes=base_classes
            )
            module.classes.append(cls)
            return inline_class_name

        if refs:
            return self._resolve_ref_type(module, schema_url, refs[0])

        return "Any"

    # -------------------------------------------------------------------------
    # Other property type resolvers
    # -------------------------------------------------------------------------

    def _resolve_any_of_property(
        self,
        module: ModuleCode,
        schema_url: str,
        prop_schema: dict[str, Any],
    ) -> str:
        """Resolve an anyOf property type."""
        any_of = prop_schema["anyOf"]
        parts: list[str] = []
        for item in any_of:
            if "$ref" in item:
                parts.append(self._resolve_ref_type(module, schema_url, item["$ref"]))
            elif "type" in item:
                parts.append(self._json_type_to_python(item["type"]))
        if len(parts) == 1:
            return parts[0]
        return _join_union(parts)

    def _resolve_one_of_property(
        self,
        module: ModuleCode,
        schema_url: str,
        prop_name: str,
        prop_schema: dict[str, Any],
    ) -> str:
        """Resolve a oneOf property type."""
        one_of = prop_schema["oneOf"]
        parts: list[str] = []
        for item in one_of:
            if "$ref" in item:
                parts.append(self._resolve_ref_type(module, schema_url, item["$ref"]))
            elif "allOf" in item:
                resolved = self._resolve_all_of_property(
                    module, schema_url, prop_name, item
                )
                if resolved:
                    parts.append(resolved)
            elif "type" in item:
                parts.append(self._json_type_to_python(item["type"]))
            elif "format" in item:
                parts.append("str")
        if len(parts) == 1:
            return parts[0]
        return _join_union(parts)

    def _resolve_array_item_type(
        self,
        module: ModuleCode,
        schema_url: str,
        items_schema: dict[str, Any],
    ) -> str:
        """Resolve the element type of an array from its items schema."""
        if "type" in items_schema:
            return self._json_type_to_python(items_schema["type"])
        if "$ref" in items_schema:
            return self._resolve_ref_type(module, schema_url, items_schema["$ref"])
        if "anyOf" in items_schema:
            parts = []
            for variant in items_schema["anyOf"]:
                if "type" in variant:
                    parts.append(self._json_type_to_python(variant["type"]))
                elif "$ref" in variant:
                    parts.append(
                        self._resolve_ref_type(module, schema_url, variant["$ref"])
                    )
            if parts:
                return _join_union(parts)
        if "oneOf" in items_schema:
            parts = []
            for variant in items_schema["oneOf"]:
                if "type" in variant:
                    parts.append(self._json_type_to_python(variant["type"]))
                elif "$ref" in variant:
                    parts.append(
                        self._resolve_ref_type(module, schema_url, variant["$ref"])
                    )
            if parts:
                return _join_union(parts)
        return "Any"

    def _resolve_array_type(
        self,
        module: ModuleCode,
        schema_url: str,
        prop_name: str,
        prop_schema: dict[str, Any],
    ) -> str:
        """Resolve an array property type."""
        items = prop_schema.get("items")
        if items is None:
            return "list[Any]"

        if "allOf" in items:
            item_type = self._resolve_all_of_array_items(
                module, schema_url, prop_name, items
            )
            return f"list[{item_type}]"

        if "$ref" in items:
            item_type = self._resolve_ref_type(module, schema_url, items["$ref"])
            return f"list[{item_type}]"

        if "type" in items:
            if items["type"] == "object" and "properties" in items:
                item_class_name = property_name_to_class_name(prop_name) + "Item"
                cls = self._generate_dataclass(
                    module, schema_url, item_class_name, items
                )
                module.classes.append(cls)
                return f"list[{item_class_name}]"
            return f"list[{self._json_type_to_python(items['type'])}]"

        if "anyOf" in items or "oneOf" in items:
            item_type = self._resolve_array_item_type(module, schema_url, items)
            return f"list[{item_type}]"

        if "properties" in items:
            item_class_name = property_name_to_class_name(prop_name) + "Item"
            cls = self._generate_dataclass(module, schema_url, item_class_name, items)
            module.classes.append(cls)
            return f"list[{item_class_name}]"

        return "list[Any]"

    def _resolve_all_of_array_items(
        self,
        module: ModuleCode,
        schema_url: str,
        prop_name: str,
        items_schema: dict[str, Any],
    ) -> str:
        """Resolve array items that use allOf (technique documents + custom props)."""
        all_of = items_schema["allOf"]

        merged_props: dict[str, Any] = {}
        merged_required: list[str] = []
        base_refs: list[str] = []

        if "properties" in items_schema:
            for pk, pv in items_schema["properties"].items():
                if pk in merged_props:
                    merged_props[pk] = _deep_merge_schemas(merged_props[pk], pv)
                else:
                    merged_props[pk] = pv
        if "required" in items_schema:
            merged_required.extend(items_schema["required"])

        for item in all_of:
            if "$ref" in item:
                base_refs.append(item["$ref"])
            if isinstance(item, dict):
                if "properties" in item:
                    for pk, pv in item["properties"].items():
                        if pk in merged_props:
                            merged_props[pk] = _deep_merge_schemas(merged_props[pk], pv)
                        else:
                            merged_props[pk] = pv
                if "required" in item:
                    merged_required.extend(item["required"])
                if "anyOf" in item:
                    self._merger.merge_any_of_variants_into_props(
                        schema_url, item["anyOf"], merged_props
                    )

        self._merger.deep_merge_base_ref_properties(schema_url, base_refs, merged_props)

        item_class_name = property_name_to_class_name(prop_name) + "Item"
        seen: set[str] = set()
        base_classes: list[str] = []
        for ref in base_refs:
            cls_name = self._resolve_ref_type(module, schema_url, ref)
            if cls_name not in seen:
                seen.add(cls_name)
                base_classes.append(cls_name)

        if merged_props:
            merged = {"type": "object", "properties": merged_props}
            if merged_required:
                merged["required"] = list(set(merged_required))
            cls = self._generate_dataclass(
                module, schema_url, item_class_name, merged, base_classes=base_classes
            )
        elif base_classes:
            cls = GeneratedClass(
                name=item_class_name,
                fields=[],
                bases=base_classes,
                dependencies=set(base_classes),
            )
        else:
            return "Any"

        module.classes.append(cls)
        return item_class_name

    # -------------------------------------------------------------------------
    # $ref resolution
    # -------------------------------------------------------------------------

    def _resolve_ref_type(
        self, module: ModuleCode, _current_schema_url: str, ref: str
    ) -> str:
        """Resolve a $ref to a Python type name, adding imports as needed."""
        ref_schema_url, def_name = parse_ref(ref)

        # Local reference within the same schema
        if ref_schema_url is None:
            if def_name:
                return def_name_to_class_name(def_name)
            return "Any"

        # External reference
        ref_module = self._modules.get(ref_schema_url)
        if ref_module and def_name and def_name in ref_module.exported_names:
            class_name = ref_module.exported_names[def_name]
            module_path = schema_url_to_module_path(ref_schema_url)
            module.imports.append(ImportEntry(module=module_path, name=class_name))
            return class_name

        # If we haven't generated the module yet (shouldn't happen with correct ordering),
        # or the definition doesn't exist, generate a best-guess name
        if def_name:
            class_name = def_name_to_class_name(def_name)
            module_path = schema_url_to_module_path(ref_schema_url)
            module.imports.append(ImportEntry(module=module_path, name=class_name))
            return class_name

        return "Any"

    # -------------------------------------------------------------------------
    # Quantity value + unit generation
    # -------------------------------------------------------------------------

    def _generate_quantity_value_type(
        self,
        module: ModuleCode,
        schema_url: str,
        quantity_ref: str,
        unit_ref: str,
    ) -> str:
        """Import a TQuantityValue{Unit} thin subclass from the shared module.

        Imports directly from shared/definitions/quantity_values.py into
        whichever module needs the type.  This avoids re-export routing
        through core.py, which would make core.py's output depend on
        which technique schemas were included in a given generation run.
        """
        _, unit_def_name = parse_ref(unit_ref)
        unit_schema_url = unit_ref.split("#")[0]
        try:
            canonical_unit_url = normalize_schema_url(unit_schema_url)
        except ValueError:
            return self._resolve_ref_type(module, schema_url, quantity_ref)

        unit_schema = self.schemas.get(canonical_unit_url, {})
        unit_def = unit_schema.get("$defs", {}).get(unit_def_name, {})
        const_value = self._extract_unit_const(unit_def)

        if const_value is None:
            return self._resolve_ref_type(module, schema_url, quantity_ref)

        class_name = self._qv_manager.get_or_create(const_value)

        # Import directly from shared quantity_values into the consuming module
        if not any(
            imp.name == class_name and imp.module == _SHARED_QUANTITY_VALUES_MODULE
            for imp in module.imports
        ):
            module.imports.append(
                ImportEntry(
                    module=_SHARED_QUANTITY_VALUES_MODULE,
                    name=class_name,
                )
            )

        return class_name

    # -------------------------------------------------------------------------
    # ADM schema generation (top-level technique schemas)
    # -------------------------------------------------------------------------

    def _generate_adm_module(
        self,
        module: ModuleCode,
        schema_url: str,
        schema: dict[str, Any],
    ) -> None:
        """Generate the top-level ADM model module.

        Flattens the root-level allOf into a synthetic schema dict and
        delegates to ``_generate_dataclass`` so field generation logic
        is not duplicated.
        """
        all_of = schema.get("allOf", [])

        all_props: dict[str, Any] = {}
        all_required: set[str] = set(schema.get("required", []))
        has_manifest = False

        for item in all_of:
            if "$ref" in item:
                _, def_name = parse_ref(item["$ref"])
                if def_name == "asm":
                    has_manifest = True
            if "properties" in item:
                all_props.update(item["properties"])
            if "required" in item:
                all_required.update(item["required"])

        has_manifest = has_manifest or "$asm.manifest" in all_required

        # Build a synthetic schema that _generate_dataclass can consume
        synthetic: dict[str, Any] = {
            "type": "object",
            "properties": all_props,
        }
        if all_required:
            synthetic["required"] = list(all_required)

        model_cls = self._generate_dataclass(
            module, schema_url, "Model", synthetic, frozen=False
        )

        # Prepend manifest field — it's always first and always required.
        # _generate_dataclass always sets fields (never None).
        if has_manifest and model_cls.fields is not None:
            manifest_field = FieldDef(
                python_name=property_name_to_python("$asm.manifest"),
                type_str="str",
                json_name="$asm.manifest",
                is_required=True,
            )
            model_cls.fields.insert(0, manifest_field)

        module.classes.append(model_cls)
        module.exported_names["Model"] = "Model"

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _json_type_to_python(self, json_type: str | list[str]) -> str:
        """Convert a JSON Schema type to a Python type annotation."""
        if isinstance(json_type, list):
            types = [self._json_type_to_python(t) for t in json_type]
            return _join_union(types)

        mapping = {
            "string": "str",
            "number": "float",
            "integer": "int",
            "boolean": "bool",
            "null": "None",
            "object": "dict[str, Any]",
            "array": "list[Any]",
        }
        return mapping.get(json_type, "Any")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _join_union(parts: list[str]) -> str:
    """Join type parts into a union string, sorted for deterministic output."""
    return " | ".join(sorted(parts))


def _make_alias(name: str, target: str) -> GeneratedClass:
    """Create a type alias GeneratedClass."""
    return GeneratedClass(
        name=name,
        alias_target=target,
        dependencies=_extract_type_references(target),
    )


def _partition_all_of(
    all_of: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    """Split allOf items into $ref strings and inline schema dicts."""
    refs: list[str] = []
    schemas: list[dict[str, Any]] = []
    for item in all_of:
        if "$ref" in item:
            refs.append(item["$ref"])
        elif isinstance(item, dict):
            schemas.append(item)
    return refs, schemas
