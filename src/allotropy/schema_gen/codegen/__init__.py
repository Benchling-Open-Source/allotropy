"""Code generation package: convert JSON Schema definitions to Python dataclass modules.

Public API — re-exports for backward compatibility with existing importers.
"""

from allotropy.schema_gen.codegen.generator import SchemaCodeGenerator
from allotropy.schema_gen.codegen.ir import (
    _all_classes_compatible,
    _extract_type_references,
    _field_declaration,
    _merge_class_fields,
    _topological_sort_classes,
    FieldDef,
    GeneratedClass,
    ImportEntry,
    ModuleCode,
    quote_python_literal,
)
from allotropy.schema_gen.codegen.merger import (
    _absolutize_refs,
    _deep_merge_schemas,
    _merge_props_into,
    _strip_required_recursive,
    SchemaMerger,
)
from allotropy.schema_gen.codegen.quantity_values import QuantityValueManager
from allotropy.schema_gen.codegen.type_resolver import extract_unit_const

# Backward-compatible aliases for renamed symbols
_all_classes_identical = _all_classes_compatible
_dquote = quote_python_literal

__all__ = [
    # generator
    "SchemaCodeGenerator",
    # ir
    "_all_classes_compatible",
    "_all_classes_identical",  # deprecated alias
    "_dquote",  # deprecated alias for quote_python_literal
    "_extract_type_references",
    "_field_declaration",
    "_merge_class_fields",
    "_topological_sort_classes",
    "FieldDef",
    "GeneratedClass",
    "ImportEntry",
    "ModuleCode",
    "quote_python_literal",
    # merger
    "_absolutize_refs",
    "_deep_merge_schemas",
    "_merge_props_into",
    "_strip_required_recursive",
    "SchemaMerger",
    # quantity_values
    "QuantityValueManager",
    # type_resolver
    "extract_unit_const",
]
