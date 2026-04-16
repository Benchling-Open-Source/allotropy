"""Type resolution engine for JSON Schema → Python type mapping.

Handles all schema-to-type dispatch: oneOf, anyOf, allOf, enum, object,
array, $ref — generating inline classes and resolving cross-module references.
"""

from __future__ import annotations

from typing import Any
import warnings

from allotropy.schema_gen.codegen.ir import (
    _extract_type_references,
    _join_union,
    _make_alias,
    _unique_ordered,
    FieldDef,
    GeneratedClass,
    ModuleCode,
    quote_python_literal,
)
from allotropy.schema_gen.codegen.merger import (
    _absolutize_refs,
    _deep_merge_schemas,
    _merge_props_into,
    _ref_base_url,
    collect_all_of_parts,
    partition_all_of,
    SchemaMerger,
)
from allotropy.schema_gen.codegen.quantity_values import (
    is_quantity_value_variant,
    QuantityValueManager,
    QV_BASE_NAMES,
)
from allotropy.schema_gen.naming import (
    def_name_to_class_name,
    normalize_schema_url,
    parse_ref,
    property_name_to_class_name,
    property_name_to_python,
    schema_url_to_module_path,
    UNITS_SCHEMA_MARKER,
)

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


def _is_constraint_only_overlay(prop_schema: dict[str, Any]) -> bool:
    """Return True if the property schema is a constraint-only overlay.

    Constraint-only overlays contain exclusively JSON Schema validation
    keywords (e.g. ``minItems``, ``maxItems``, ``required``) that refine
    a field already defined on a base class.  They do not introduce a new
    type and should be skipped during code generation.

    An empty schema (e.g. after stripping ``$asm`` metadata) is NOT a
    constraint overlay — it represents a real field typed as ``Any``.
    """
    return bool(prop_schema) and prop_schema.keys() <= _CONSTRAINT_ONLY_KEYS


def extract_unit_const(schema: dict[str, Any]) -> str | None:
    """Extract the const unit value from a unit ``$defs`` entry.

    Used by both the code generator and the standalone units module
    generator in ``generate.py``.
    """
    props = schema.get("properties", {})
    unit_prop = props.get("unit", {})
    result: str | None = unit_prop.get("const")
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
SHARED_DEFINITION_TYPES: dict[str, str] = {
    "tQuantityValue": "TQuantityValue",
    "tStatisticDatumRole": "TStatisticDatumRole",
    "tClass": "TClass",
    "tUnit": "TUnit",
}

SHARED_DEFINITIONS_MODULE = "allotropy.allotrope.models.shared.definitions.definitions"

# Shared module where TQuantityValue{Unit} thin subclasses live.
# The codegen imports from here rather than generating subclasses in each
# core.py.  When a schema introduces a unit not yet in this module, the
# codegen records it and generate.py appends the new class.
SHARED_QUANTITY_VALUES_MODULE = (
    "allotropy.allotrope.models.shared.definitions.quantity_values"
)

# JSON type → Python type mapping (module constant, not recreated per call)
_JSON_TYPE_MAP: dict[str, str] = {
    "string": "str",
    "number": "float",
    "integer": "int",
    "boolean": "bool",
    "null": "None",
    "object": "dict[str, Any]",
    "array": "list[Any]",
}


# ---------------------------------------------------------------------------
# TypeResolver
# ---------------------------------------------------------------------------


class TypeResolver:
    """Resolves JSON Schema definitions and properties to Python types.

    Handles all schema-to-type mapping: dispatching on schema patterns
    (oneOf, anyOf, allOf, enum, object, array, $ref), generating inline
    classes, and resolving cross-module references.

    This class is the engine of type generation — it is created and driven
    by :class:`SchemaCodeGenerator`, which handles module-level orchestration.
    The *export_map* is a pre-computed, immutable mapping of
    ``{schema_url: {def_name: class_name}}`` built during analysis before
    any code generation starts, so name resolution is independent of
    generation order.
    """

    def __init__(
        self,
        schemas: dict[str, dict[str, Any]],
        export_map: dict[str, dict[str, str]],
        merger: SchemaMerger,
        qv_manager: QuantityValueManager,
    ) -> None:
        self._schemas = schemas
        self._export_map = export_map
        self._merger = merger
        self._qv_manager = qv_manager

    # -------------------------------------------------------------------------
    # Type dispatch (entry point from SchemaCodeGenerator)
    # -------------------------------------------------------------------------

    def generate_type(
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
            return self.generate_dataclass(module, schema_url, class_name, schema)

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
            return self.generate_dataclass(module, schema_url, class_name, schema)

        # Conditional validation constraints (if/then) don't produce types —
        # they refine allowed values based on sibling fields (e.g., cFillValue*
        # constrains $asm.fill-value based on @componentDatatype).
        if "if" in schema and "then" in schema:
            return None

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

        parts: list[str] = []

        # If there's a primitive + object variant, generate a typed item class
        if primitive_types and object_schemas:
            item_class_name = f"{class_name}Item"
            item_cls = self.generate_dataclass(
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
                return self.generate_dataclass(
                    module, schema_url, class_name, object_schemas[0]
                )
            # Multiple object variants — merge all properties
            merged_props: dict[str, Any] = {}
            for obj_schema in object_schemas:
                _merge_props_into(merged_props, obj_schema.get("properties", {}))
            merged = {"type": "object", "properties": merged_props}
            return self.generate_dataclass(module, schema_url, class_name, merged)

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
                _merge_props_into(merged_props, item["properties"])
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
        return self.generate_dataclass(
            module, schema_url, class_name, merged, base_classes=base_classes
        )

    # -------------------------------------------------------------------------
    # Object → dataclass generation
    # -------------------------------------------------------------------------

    def generate_dataclass(
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
            cls = self.generate_dataclass(
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
            cls = self.generate_dataclass(
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
            literals = ", ".join(quote_python_literal(v) for v in values)
            return f"Literal[{literals}]"
        if "const" in prop_schema:
            return f"Literal[{quote_python_literal(prop_schema['const'])}]"

        # Simple types
        if "type" in prop_schema:
            return self._json_type_to_python(prop_schema["type"])

        # Format-based type
        if "format" in prop_schema:
            return "str"

        if _is_constraint_only_overlay(prop_schema):
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
        refs, inline_schemas = partition_all_of(all_of)

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

    @staticmethod
    def _is_units_ref(ref: str) -> bool:
        """Return True if *ref* points to a units schema definition."""
        schema_url = _ref_base_url(ref)
        if not schema_url:
            return False
        try:
            return UNITS_SCHEMA_MARKER in normalize_schema_url(schema_url)
        except ValueError:
            return False

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

        Recognises both tQuantityValue and tNullableQuantityValue (treated
        identically — the nullable distinction was removed).
        """
        qv_base_names = {n.lower() for n in QV_BASE_NAMES}
        quantity_ref = None
        unit_refs: list[str] = []
        for ref in refs:
            _, def_name = parse_ref(ref)
            if def_name and def_name.lower() in qv_base_names:
                quantity_ref = ref
            elif def_name and self._is_units_ref(ref):
                unit_refs.append(ref)

        # Also collect unit refs from inline oneOf schemas — deep-merge
        # accumulation can produce allOf entries with both direct unit $refs
        # AND inline {oneOf: [unit1, unit2]} schemas.
        for s in inline_schemas:
            if "oneOf" in s:
                for variant in s["oneOf"]:
                    if "$ref" in variant and self._is_units_ref(variant["$ref"]):
                        unit_refs.append(variant["$ref"])

        if not quantity_ref:
            return None

        if not unit_refs:
            return None

        if len(unit_refs) == 1:
            return self._generate_quantity_value_type(
                module, schema_url, quantity_ref, unit_refs[0]
            )

        types = [
            self._generate_quantity_value_type(module, schema_url, quantity_ref, uref)
            for uref in unit_refs
        ]
        return _join_union(_unique_ordered(types))

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

        literals = ", ".join(quote_python_literal(v) for v in enum_values)
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
        merged_props, merged_required, base_refs = collect_all_of_parts(
            prop_schema, all_of
        )
        # Merge variant properties from anyOf/oneOf within allOf items
        for item in all_of:
            if isinstance(item, dict):
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
                    ref_base_url_str = _ref_base_url(ref)
                    ref_schema = self._merger.resolve_ref_to_schema(schema_url, ref)
                    if ref_schema and "properties" in ref_schema:
                        ref_props = ref_schema["properties"]
                        if ref_base_url_str:
                            ref_props = {
                                k: _absolutize_refs(v, ref_base_url_str)
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
                merged["required"] = sorted(set(merged_required))
            cls = self.generate_dataclass(
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
        parts = self._resolve_variant_types(module, schema_url, prop_schema["anyOf"])
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
        for variant_key in ("anyOf", "oneOf"):
            if variant_key in items_schema:
                parts = self._resolve_variant_types(
                    module, schema_url, items_schema[variant_key]
                )
                if parts:
                    return _join_union(parts)
        return "Any"

    def _resolve_variant_types(
        self,
        module: ModuleCode,
        schema_url: str,
        variants: list[dict[str, Any]],
    ) -> list[str]:
        """Resolve a list of anyOf/oneOf variants to Python type strings."""
        parts: list[str] = []
        for variant in variants:
            if "type" in variant:
                parts.append(self._json_type_to_python(variant["type"]))
            elif "$ref" in variant:
                parts.append(
                    self._resolve_ref_type(module, schema_url, variant["$ref"])
                )
        return parts

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

        if "type" in items and items["type"] == "object" and "properties" in items:
            item_class_name = property_name_to_class_name(prop_name) + "Item"
            cls = self.generate_dataclass(module, schema_url, item_class_name, items)
            module.classes.append(cls)
            return f"list[{item_class_name}]"

        if "type" in items:
            return f"list[{self._json_type_to_python(items['type'])}]"

        if "anyOf" in items or "oneOf" in items:
            item_type = self._resolve_array_item_type(module, schema_url, items)
            return f"list[{item_type}]"

        if "properties" in items:
            item_class_name = property_name_to_class_name(prop_name) + "Item"
            cls = self.generate_dataclass(module, schema_url, item_class_name, items)
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

        merged_props, merged_required, base_refs = collect_all_of_parts(
            items_schema, all_of
        )
        # Merge anyOf variants as optional fields
        for item in all_of:
            if isinstance(item, dict) and "anyOf" in item:
                self._merger.merge_any_of_variants_into_props(
                    schema_url, item["anyOf"], merged_props
                )

        self._merger.deep_merge_base_ref_properties(schema_url, base_refs, merged_props)

        item_class_name = property_name_to_class_name(prop_name) + "Item"
        base_classes = _unique_ordered(
            [self._resolve_ref_type(module, schema_url, ref) for ref in base_refs]
        )

        if merged_props:
            merged = {"type": "object", "properties": merged_props}
            if merged_required:
                merged["required"] = sorted(set(merged_required))
            cls = self.generate_dataclass(
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
        """Resolve a $ref to a Python type name, adding imports as needed.

        Uses the pre-computed ``_export_map`` for name resolution, so this
        method is independent of generation order.
        """
        ref_schema_url, def_name = parse_ref(ref)

        # Local reference within the same schema
        if ref_schema_url is None:
            if def_name:
                return def_name_to_class_name(def_name)
            return "Any"

        # External reference — look up in pre-computed export map
        schema_exports = self._export_map.get(ref_schema_url)
        if schema_exports and def_name and def_name in schema_exports:
            class_name = schema_exports[def_name]
            module_path = schema_url_to_module_path(ref_schema_url)
            module.add_import(module_path, class_name)
            return class_name

        # Some BENCHLING schemas reference pre-composed QV variant defs
        # (e.g. core.schema#/$defs/tQuantityValueUnitless) that don't actually
        # exist as $defs in core.schema.  Route these to shared instead.
        if def_name and is_quantity_value_variant(def_name):
            class_name = def_name_to_class_name(def_name)
            module.add_import(SHARED_QUANTITY_VALUES_MODULE, class_name)
            return class_name

        # If the definition doesn't exist in the export map, generate a best-guess name
        if def_name:
            class_name = def_name_to_class_name(def_name)
            module_path = schema_url_to_module_path(ref_schema_url)
            module.add_import(module_path, class_name)
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
        unit_schema_url = _ref_base_url(unit_ref)
        try:
            canonical_unit_url = normalize_schema_url(unit_schema_url)
        except ValueError:
            return self._resolve_ref_type(module, schema_url, quantity_ref)

        unit_schema = self._schemas.get(canonical_unit_url, {})
        unit_def = unit_schema.get("$defs", {}).get(unit_def_name, {})
        const_value = extract_unit_const(unit_def)

        if const_value is None:
            return self._resolve_ref_type(module, schema_url, quantity_ref)

        class_name = self._qv_manager.get_or_create(const_value)

        # Import directly from shared quantity_values into the consuming module.
        # Duplicate imports are deduplicated by ModuleCode.render().
        module.add_import(SHARED_QUANTITY_VALUES_MODULE, class_name)

        return class_name

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def _json_type_to_python(self, json_type: str | list[str]) -> str:
        """Convert a JSON Schema type to a Python type annotation."""
        if isinstance(json_type, list):
            types = [self._json_type_to_python(t) for t in json_type]
            return _join_union(types)
        return _JSON_TYPE_MAP.get(json_type, "Any")
