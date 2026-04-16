"""Intermediate Representation types for generated Python modules.

Defines the data structures that represent generated code: fields, classes,
imports, and modules. Also contains rendering, deduplication, and topological
sorting logic that operates purely on these IR types.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import re
from typing import Any

from allotropy.schema_gen.naming import default_json_name


def quote_python_literal(value: Any) -> str:
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


def _unique_ordered(items: list[str]) -> list[str]:
    """Deduplicate a list while preserving insertion order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# IR data structures
# ---------------------------------------------------------------------------


@dataclass
class FieldDef:
    """A single field in a generated dataclass."""

    python_name: str
    type_str: str
    json_name: str
    is_required: bool


@dataclass
class ImportEntry:
    """A Python import to add to a generated module."""

    module: str  # Full module path (e.g., "allotropy.allotrope.models.adm.core...")
    name: str  # Class/type name to import
    reexport: bool = False  # If True, emit "import X as X" for mypy explicit re-export


@dataclass
class GeneratedClass:
    """A generated Python class, type alias, or enum.

    At most one of ``fields``, ``enum_members``, or ``alias_target`` is
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
    # The parent $def class name that generated this inline class.
    # Used during dedup to create meaningful variant suffixes
    # (e.g., PeakItem from Millivolts $def → PeakItemMillivolts).
    source_context: str | None = None

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
                f"At most one must be populated."
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
                lines.append(f"    {member_name} = {quote_python_literal(value)}")
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
            source_context=self.source_context,
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

    def add_import(self, module: str, name: str, *, reexport: bool = False) -> None:
        """Register an import for this module."""
        self.imports.append(ImportEntry(module=module, name=name, reexport=reexport))

    def render(self, models_package: str = "allotropy.allotrope.models") -> str:
        """Render the complete Python module source code.

        This method is pure — it does not mutate ``self.classes``.
        """
        classes = _topological_sort_classes(_deduplicate_classes(self.classes))

        has_reexports = any(imp.reexport for imp in self.imports)

        lines: list[str] = []
        lines.append("# generated by allotropy.schema_gen")
        if has_reexports:
            lines.append(
                "# Re-exports imported types so downstream modules can import from here."
            )
            lines.append("# ruff: noqa: F401")
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

        # Write stdlib imports
        for stdlib_imp in sorted(stdlib_imports):
            lines.append(stdlib_imp)
        if stdlib_imports:
            lines.append("")

        # Write external imports
        for module in sorted(external_imports.keys()):
            names = sorted(external_imports[module])
            if len(names) == 1:
                lines.append(f"from {module} import {names[0]}")
            else:
                lines.append(f"from {module} import (")
                for name in names:
                    lines.append(f"    {name},")
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


# ---------------------------------------------------------------------------
# Field rendering
# ---------------------------------------------------------------------------


def _field_declaration(
    python_name: str, type_str: str, json_name: str, *, is_required: bool
) -> str:
    """Generate a dataclass field declaration, with JSON name metadata when needed.

    Omits json_name when the mapping is a straightforward space-to-underscore
    conversion. Only emits metadata for non-trivial name transformations.
    """
    needs_json_name = json_name != default_json_name(python_name)
    if needs_json_name:
        metadata = f'{{"json_name": {quote_python_literal(json_name)}}}'
        if is_required:
            return f"    {python_name}: {type_str} = field(metadata={metadata})"
        return f"    {python_name}: {type_str} | None = field(default=None, metadata={metadata})"
    if is_required:
        return f"    {python_name}: {type_str}"
    return f"    {python_name}: {type_str} | None = None"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _deduplicate_classes(classes: list[GeneratedClass]) -> list[GeneratedClass]:
    """Deduplicate classes by name, handling identical, variant, and widening cases.

    Same-named classes are grouped and resolved using one of three strategies:

    1. **Identical merge**: All copies are type-compatible — merge field sets
       (one copy may have extra fields from a deeper schema branch).
    2. **Variant split**: Conflicting classes with ``source_context`` from
       sub-schema ``$defs`` become distinct variant classes plus a union
       type alias preserving field-type correlation.
    3. **Widening merge**: Technique-level duplicates without source_context
       are merged with conflicting types combined into unions.
    """
    groups: dict[str, list[GeneratedClass]] = defaultdict(list)
    for cls in classes:
        groups[cls.name].append(cls)

    unique: list[GeneratedClass] = []
    for name, group in groups.items():
        if len(group) == 1:
            unique.append(group[0].copy())
            continue

        if _all_classes_compatible(group):
            merged = group[0].copy()
            for other in group[1:]:
                _merge_class_fields(merged, other)
            unique.append(merged)
            continue

        all_have_context = all(cls.source_context for cls in group)
        if all_have_context:
            variant_names: list[str] = []
            for cls in group:
                variant_name = f"{name}{cls.source_context}"
                variant_cls = cls.copy()
                variant_cls.name = variant_name
                unique.append(variant_cls)
                variant_names.append(variant_name)

            unique.append(
                GeneratedClass(
                    name=name,
                    alias_target=_join_union(variant_names),
                    dependencies=set(variant_names),
                )
            )
        else:
            merged = group[0].copy()
            for other in group[1:]:
                _widen_class_fields(merged, other)
            unique.append(merged)

    return unique


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


def _all_classes_compatible(group: list[GeneratedClass]) -> bool:
    """True if all classes in *group* are type-compatible on shared fields.

    Classes are compatible when every field name present in more than one
    class has the same type string in all classes.  Extra fields in one
    class are allowed (they'll be merged).  Used during dedup to decide
    whether same-named classes can be merged (compatible) or must become
    distinct variant classes (conflicting).
    """
    if len(group) <= 1:
        return True
    # Build per-class field→type maps
    maps: list[dict[str, str] | None] = []
    for cls in group:
        if cls.fields is None:
            maps.append(None)
        else:
            maps.append({f.python_name: f.type_str for f in cls.fields})

    # All must be the same kind (dataclass vs alias/enum)
    if any(m is None for m in maps) and any(m is not None for m in maps):
        return False

    # Compare shared field types pairwise against the first
    ref = maps[0]
    if ref is None:
        return True
    for other in maps[1:]:
        if other is None:
            continue
        for name, type_str in other.items():
            if name in ref and ref[name] != type_str:
                return False
    return True


def _widen_class_fields(existing: GeneratedClass, new: GeneratedClass) -> None:
    """Merge fields from *new* into *existing*, widening types as unions on conflict.

    Used for technique-level anyOf merges where same-named classes from
    different variants have different field types.  Conflicting types are
    combined into a union (e.g., ``TQuantityValueMV`` + ``TQuantityValueNC``
    → ``TQuantityValueMV | TQuantityValueNC``).
    """
    if existing.fields is None or new.fields is None:
        return

    existing_by_name = {f.python_name: f for f in existing.fields}
    for f in new.fields:
        prev = existing_by_name.get(f.python_name)
        if prev is None:
            existing.fields.append(f)
            existing_by_name[f.python_name] = f
        elif prev.type_str != f.type_str:
            # Widen to union of both types, deduplicating components
            prev_parts = [p.strip() for p in prev.type_str.split("|")]
            new_parts = [p.strip() for p in f.type_str.split("|")]
            combined = _unique_ordered(prev_parts + new_parts)
            prev.type_str = _join_union(combined)
            # Mark optional if either side is optional
            if not f.is_required:
                prev.is_required = False

    existing.dependencies |= new.dependencies


def _merge_class_fields(existing: GeneratedClass, new: GeneratedClass) -> None:
    """Merge fields from *new* into *existing*, deduplicating by field name.

    Only operates on dataclasses (``fields is not None``).  Type aliases
    and enums are left unchanged.  Warns when both classes define the same
    field with a different type string.
    """
    if existing.fields is None or new.fields is None:
        return

    existing_by_name = {f.python_name: f for f in existing.fields}
    for f in new.fields:
        prev = existing_by_name.get(f.python_name)
        if prev is None:
            existing.fields.append(f)
            existing_by_name[f.python_name] = f
        elif prev.type_str != f.type_str:
            msg = (
                f"Internal error: _merge_class_fields called on non-identical "
                f"classes {existing.name!r}: field {f.python_name!r} has type "
                f"{prev.type_str!r} vs {f.type_str!r}. "
                f"This should have been caught by _all_classes_compatible."
            )
            raise ValueError(msg)

    # Merge dependencies
    existing.dependencies |= new.dependencies


# ---------------------------------------------------------------------------
# Shared helpers
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
