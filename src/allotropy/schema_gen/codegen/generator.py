"""Module-level code generation orchestrator.

Iterates schemas in dependency order, handles shared definition imports,
ADM root flattening, and delegates type-level generation to TypeResolver.
"""

from __future__ import annotations

from typing import Any

from allotropy.schema_gen.codegen.ir import (
    FieldDef,
    ModuleCode,
)
from allotropy.schema_gen.codegen.merger import (
    _merge_props_into,
    SchemaMerger,
)
from allotropy.schema_gen.codegen.quantity_values import QuantityValueManager
from allotropy.schema_gen.codegen.type_resolver import (
    SHARED_DEFINITION_TYPES,
    SHARED_DEFINITIONS_MODULE,
    TypeResolver,
)
from allotropy.schema_gen.naming import (
    def_name_to_class_name,
    property_name_to_python,
    UNITS_SCHEMA_MARKER,
)


class SchemaCodeGenerator:
    """Generates Python modules from a set of JSON schemas.

    Orchestrates module-level generation: iterates schemas in dependency
    order, handles shared definition imports, ADM root flattening, and
    delegates type-level generation to :class:`TypeResolver`.

    Constructs a static ``_export_map`` before code generation starts so
    that name resolution in :class:`TypeResolver` is independent of the
    order in which modules are generated.
    """

    def __init__(
        self,
        schemas: dict[str, dict[str, Any]],
        generation_order: list[str],
        models_package: str = "allotropy.allotrope.models",
        unit_descriptive_names: dict[str, str] | None = None,
    ) -> None:
        self.schemas = schemas
        self.generation_order = generation_order
        self.models_package = models_package
        # Track generated modules (output-only accumulator)
        self._modules: dict[str, ModuleCode] = {}
        # Schema merging helper
        self._merger = SchemaMerger(schemas)
        # Quantity value lifecycle manager
        self._qv_manager = QuantityValueManager(unit_descriptive_names)
        # Pre-compute export map before code generation starts
        self._export_map: dict[str, dict[str, str]] = self._analyze_exports()
        self._type_resolver = TypeResolver(
            schemas, self._export_map, self._merger, self._qv_manager
        )

    def _analyze_exports(self) -> dict[str, dict[str, str]]:
        """Pre-compute {schema_url: {def_name: class_name}} for all schemas.

        Builds a complete, immutable mapping of every schema's exported
        names before any code generation starts.  This lets TypeResolver
        resolve cross-module references without depending on the mutable
        ``_modules`` dict or on generation order.
        """
        result: dict[str, dict[str, str]] = {}
        for url in self.generation_order:
            schema = self.schemas[url]
            defs = schema.get("$defs", {})
            exports: dict[str, str] = {}
            for def_name in defs:
                if def_name in SHARED_DEFINITION_TYPES:
                    exports[def_name] = SHARED_DEFINITION_TYPES[def_name]
                else:
                    exports[def_name] = def_name_to_class_name(def_name)
            result[url] = exports
        return result

    @property
    def new_quantity_value_classes(self) -> list[tuple[str, str]]:
        return self._qv_manager.new_classes

    @property
    def all_quantity_value_classes(self) -> dict[str, str]:
        """All known TQuantityValue classes: {unit_string: class_name}."""
        return self._qv_manager.all_classes

    def ensure_quantity_value_class(self, unit_const: str) -> str:
        """Ensure a TQuantityValue class exists for *unit_const*."""
        return self._qv_manager.get_or_create(unit_const)

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
            # Units are handled by the shared units module (shared/definitions/units.py),
            # not generated per-schema.  Skip — no module output needed.
            pass
        else:
            # Generate $defs classes if present (core, hierarchy, detector types, etc.)
            if defs:
                self._generate_defs_module(module, schema_url, defs)
            # Generate ADM top-level Model class if this is a technique schema
            if self._is_adm_schema(schema):
                self._generate_adm_module(module, schema_url, schema)

        return module

    def _is_units_schema(self, url: str) -> bool:
        return UNITS_SCHEMA_MARKER in url

    @staticmethod
    def _is_adm_schema(schema: dict[str, Any]) -> bool:
        """Check if this is a top-level ADM schema (has allOf at root)."""
        return "allOf" in schema

    # -------------------------------------------------------------------------
    # Regular $defs module generation (core, cube, hierarchy, manifest, detector)
    # -------------------------------------------------------------------------

    def _generate_defs_module(
        self, module: ModuleCode, schema_url: str, defs: dict[str, Any]
    ) -> None:
        """Generate classes for all $defs in a schema."""
        for def_name, def_schema in defs.items():
            if not isinstance(def_schema, dict):
                continue

            # Import shared definition types instead of regenerating them.
            # Re-exported here so downstream generated modules can import
            # from this core module without needing to know the source.
            if def_name in SHARED_DEFINITION_TYPES:
                class_name = SHARED_DEFINITION_TYPES[def_name]
                module.add_import(SHARED_DEFINITIONS_MODULE, class_name, reexport=True)
                module.exported_names[def_name] = class_name
                continue

            class_name = def_name_to_class_name(def_name)
            start_idx = len(module.classes)
            cls = self._type_resolver.generate_type(
                module, schema_url, class_name, def_schema
            )
            if cls:
                module.classes.append(cls)
                module.exported_names[def_name] = class_name
            # Tag inline classes generated as children of this $def with
            # their source context so variant dedup can create meaningful
            # suffixes (e.g., PeakItem from Millivolts → PeakItemMillivolts).
            for c in module.classes[start_idx:]:
                if c.source_context is None:
                    c.source_context = class_name

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

        for item in all_of:
            if "$ref" in item:
                ref_schema = self._merger.resolve_ref_to_schema(
                    schema_url, item["$ref"]
                )
                if ref_schema:
                    _merge_props_into(all_props, ref_schema.get("properties", {}))
                    all_required.update(ref_schema.get("required", []))
            if "properties" in item:
                _merge_props_into(all_props, item["properties"])
            if "required" in item:
                all_required.update(item["required"])

        has_manifest = "$asm.manifest" in all_props or "$asm.manifest" in all_required

        # Build a synthetic schema that _generate_dataclass can consume
        synthetic: dict[str, Any] = {
            "type": "object",
            "properties": all_props,
        }
        if all_required:
            synthetic["required"] = list(all_required)

        model_cls = self._type_resolver.generate_dataclass(
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
