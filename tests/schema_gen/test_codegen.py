"""Tests for allotropy.schema_gen.codegen — code generation from JSON schemas."""

from __future__ import annotations

from typing import Any

import pytest

from allotropy.schema_gen.codegen import (
    _absolutize_refs,
    _deep_merge_schemas,
    _dquote,
    _field_declaration,
    _merge_class_fields,
    _strip_required_recursive,
    _topological_sort_classes,
    FieldDef,
    GeneratedClass,
    ImportEntry,
    ModuleCode,
    QuantityValueManager,
    SchemaCodeGenerator,
    SchemaMerger,
)

BASE = "http://purl.allotrope.org/json-schemas/"
CORE_URL = f"{BASE}adm/core/REC/2024/09/core.schema"
UNITS_URL = f"{BASE}qudt/REC/2024/09/units.schema"


# ---------------------------------------------------------------------------
# _dquote
# ---------------------------------------------------------------------------


class TestDquote:
    def test_simple_string(self) -> None:
        assert _dquote("hello") == '"hello"'

    def test_string_with_double_quotes(self) -> None:
        result = _dquote('say "hi"')
        assert result == "'say \"hi\"'"

    def test_non_string(self) -> None:
        assert _dquote(42) == "42"

    def test_bool(self) -> None:
        assert _dquote(True) == "True"  # noqa: FBT003

    def test_backslash(self) -> None:
        result = _dquote("a\\b")
        assert "\\\\" in result

    def test_empty_string(self) -> None:
        assert _dquote("") == '""'


# ---------------------------------------------------------------------------
# _field_declaration
# ---------------------------------------------------------------------------


class TestFieldDeclaration:
    def test_required_simple_name(self) -> None:
        result = _field_declaration(
            "device_type", "str", "device type", is_required=True
        )
        assert result == "    device_type: str"
        assert "field(" not in result

    def test_optional_simple_name(self) -> None:
        result = _field_declaration(
            "device_type", "str", "device type", is_required=False
        )
        assert result == "    device_type: str | None = None"
        assert "field(" not in result

    def test_required_non_trivial_name(self) -> None:
        result = _field_declaration(
            "field_asm_manifest", "str", "$asm.manifest", is_required=True
        )
        assert "field(metadata=" in result
        assert '"$asm.manifest"' in result

    def test_optional_non_trivial_name(self) -> None:
        result = _field_declaration(
            "cube_structure", "TDatacubeStructure", "cube-structure", is_required=False
        )
        assert "field(default=None, metadata=" in result
        assert '"cube-structure"' in result

    def test_at_type_json_name(self) -> None:
        result = _field_declaration("field_type", "str", "@type", is_required=True)
        assert '"@type"' in result
        assert "field(metadata=" in result

    def test_pco2_needs_metadata(self) -> None:
        result = _field_declaration(
            "p_co2", "TQuantityValueMmHg", "pCO2", is_required=False
        )
        assert '"pCO2"' in result


# ---------------------------------------------------------------------------
# _strip_required_recursive
# ---------------------------------------------------------------------------


class TestStripRequiredRecursive:
    def test_removes_required(self) -> None:
        schema = {"properties": {"a": {}}, "required": ["a"]}
        result = _strip_required_recursive(schema)
        assert "required" not in result
        assert "properties" in result

    def test_nested_required(self) -> None:
        schema = {
            "properties": {"a": {"properties": {"b": {}}, "required": ["b"]}},
            "required": ["a"],
        }
        result = _strip_required_recursive(schema)
        assert "required" not in result
        assert "required" not in result["properties"]["a"]

    def test_list_with_required(self) -> None:
        schema = [{"required": ["a"]}, {"required": ["b"]}]
        result = _strip_required_recursive(schema)
        assert all("required" not in item for item in result)

    def test_preserves_non_required_keys(self) -> None:
        schema = {"type": "object", "properties": {"x": {}}, "required": ["x"]}
        result = _strip_required_recursive(schema)
        assert result["type"] == "object"
        assert "x" in result["properties"]


# ---------------------------------------------------------------------------
# _absolutize_refs
# ---------------------------------------------------------------------------


class TestAbsolutizeRefs:
    def test_rewrites_local_ref(self) -> None:
        schema: dict[str, Any] = {"$ref": "#/$defs/foo"}
        result = _absolutize_refs(schema, "http://example.com/bar.schema")
        assert result["$ref"] == "http://example.com/bar.schema#/$defs/foo"

    def test_leaves_absolute_ref(self) -> None:
        schema: dict[str, Any] = {"$ref": "http://other.com#/$defs/foo"}
        result = _absolutize_refs(schema, "http://example.com/bar.schema")
        assert result["$ref"] == "http://other.com#/$defs/foo"

    def test_nested_refs(self) -> None:
        schema: dict[str, Any] = {
            "properties": {"a": {"$ref": "#/$defs/x"}, "b": {"type": "string"}}
        }
        result = _absolutize_refs(schema, "http://base")
        assert result["properties"]["a"]["$ref"] == "http://base#/$defs/x"
        assert result["properties"]["b"] == {"type": "string"}

    def test_list_items(self) -> None:
        schema: list[dict[str, Any]] = [{"$ref": "#/$defs/a"}, {"$ref": "#/$defs/b"}]
        result = _absolutize_refs(schema, "http://base")
        assert result[0]["$ref"] == "http://base#/$defs/a"
        assert result[1]["$ref"] == "http://base#/$defs/b"


# ---------------------------------------------------------------------------
# _deep_merge_schemas
# ---------------------------------------------------------------------------


class TestDeepMergeSchemas:
    def test_overlay_adds_new_property(self) -> None:
        base = {"properties": {"a": {"type": "string"}}}
        overlay = {"properties": {"b": {"type": "integer"}}}
        result = _deep_merge_schemas(base, overlay)
        assert "a" in result["properties"]
        assert "b" in result["properties"]

    def test_overlay_overrides_property(self) -> None:
        base = {"properties": {"a": {"type": "string"}}}
        overlay = {"properties": {"a": {"type": "integer"}}}
        result = _deep_merge_schemas(base, overlay)
        assert result["properties"]["a"]["type"] == "integer"

    def test_required_union_mode(self) -> None:
        base = {"required": ["a", "b"]}
        overlay = {"required": ["b", "c"]}
        result = _deep_merge_schemas(base, overlay)
        assert set(result["required"]) == {"a", "b", "c"}

    def test_required_intersection_mode(self) -> None:
        base = {"required": ["a", "b"]}
        overlay = {"required": ["b", "c"]}
        result = _deep_merge_schemas(base, overlay, any_of=True)
        assert set(result["required"]) == {"b"}

    def test_anyof_base_has_required_overlay_does_not(self) -> None:
        base: dict[str, Any] = {"required": ["a", "b"]}
        overlay: dict[str, Any] = {"properties": {"x": {}}}
        result = _deep_merge_schemas(base, overlay, any_of=True)
        assert result["required"] == []

    def test_anyof_overlay_has_required_base_does_not(self) -> None:
        base: dict[str, Any] = {"properties": {"a": {}}}
        overlay: dict[str, Any] = {"required": ["a"]}
        result = _deep_merge_schemas(base, overlay, any_of=True)
        # Intersection with empty set is empty
        assert "required" not in result or result.get("required") == []

    def test_items_merge(self) -> None:
        base: dict[str, Any] = {"items": {"properties": {"a": {}}}}
        overlay: dict[str, Any] = {"items": {"properties": {"b": {}}}}
        result = _deep_merge_schemas(base, overlay)
        assert "a" in result["items"]["properties"]
        assert "b" in result["items"]["properties"]

    def test_non_dict_overlay_key(self) -> None:
        base = {"type": "string"}
        overlay = {"type": "integer", "description": "new"}
        result = _deep_merge_schemas(base, overlay)
        assert result["type"] == "integer"
        assert result["description"] == "new"


# ---------------------------------------------------------------------------
# _topological_sort_classes
# ---------------------------------------------------------------------------


class TestTopologicalSortClasses:
    def test_independent_classes(self) -> None:
        classes = [
            GeneratedClass(name="B", fields=[]),
            GeneratedClass(name="A", fields=[]),
        ]
        result = _topological_sort_classes(classes)
        names = [c.name for c in result]
        # Alphabetical tie-breaking for independent classes
        assert names == ["A", "B"]

    def test_dependency_ordering(self) -> None:
        classes = [
            GeneratedClass(
                name="Child", fields=[], bases=["Parent"], dependencies={"Parent"}
            ),
            GeneratedClass(name="Parent", fields=[]),
        ]
        result = _topological_sort_classes(classes)
        names = [c.name for c in result]
        assert names.index("Parent") < names.index("Child")

    def test_type_alias_ordering(self) -> None:
        classes = [
            GeneratedClass(
                name="MyUnion",
                alias_target="TypeA | TypeB",
                dependencies={"TypeA", "TypeB"},
            ),
            GeneratedClass(name="TypeA", fields=[]),
            GeneratedClass(name="TypeB", fields=[]),
        ]
        result = _topological_sort_classes(classes)
        names = [c.name for c in result]
        assert names.index("TypeA") < names.index("MyUnion")
        assert names.index("TypeB") < names.index("MyUnion")


# ---------------------------------------------------------------------------
# _merge_class_fields
# ---------------------------------------------------------------------------


class TestMergeClassFields:
    def test_adds_new_field(self) -> None:
        existing = GeneratedClass(
            name="Foo",
            fields=[
                FieldDef(
                    python_name="a", type_str="str", json_name="a", is_required=True
                ),
            ],
        )
        new = GeneratedClass(
            name="Foo",
            fields=[
                FieldDef(
                    python_name="a", type_str="str", json_name="a", is_required=True
                ),
                FieldDef(
                    python_name="b", type_str="int", json_name="b", is_required=False
                ),
            ],
        )
        _merge_class_fields(existing, new)
        assert existing.fields is not None
        names = [f.python_name for f in existing.fields]
        assert "a" in names
        assert "b" in names

    def test_no_duplicate_fields(self) -> None:
        existing = GeneratedClass(
            name="Foo",
            fields=[
                FieldDef(
                    python_name="a", type_str="str", json_name="a", is_required=True
                ),
            ],
        )
        new = GeneratedClass(
            name="Foo",
            fields=[
                FieldDef(
                    python_name="a", type_str="str", json_name="a", is_required=True
                ),
            ],
        )
        _merge_class_fields(existing, new)
        assert existing.fields is not None
        a_count = sum(1 for f in existing.fields if f.python_name == "a")
        assert a_count == 1

    def test_required_before_optional(self) -> None:
        existing = GeneratedClass(
            name="Foo",
            fields=[
                FieldDef(
                    python_name="a", type_str="str", json_name="a", is_required=False
                ),
            ],
        )
        new = GeneratedClass(
            name="Foo",
            fields=[
                FieldDef(
                    python_name="b", type_str="str", json_name="b", is_required=True
                ),
            ],
        )
        _merge_class_fields(existing, new)
        # Render and check that required fields come before optional
        rendered = existing.render()
        lines = rendered.split("\n")
        field_lines = [
            line
            for line in lines
            if ": " in line and not line.strip().startswith(("class", "@"))
        ]
        req_indices = [
            i
            for i, line in enumerate(field_lines)
            if "= None" not in line and "= field(" not in line
        ]
        opt_indices = [
            i
            for i, line in enumerate(field_lines)
            if "= None" in line or "default=None" in line
        ]
        if req_indices and opt_indices:
            assert max(req_indices) < min(opt_indices)


# ---------------------------------------------------------------------------
# ModuleCode.render
# ---------------------------------------------------------------------------


class TestModuleCodeRender:
    def test_empty_module(self) -> None:
        module = ModuleCode(schema_url="http://test")
        result = module.render()
        assert "from __future__ import annotations" in result

    def test_renders_class(self) -> None:
        module = ModuleCode(schema_url="http://test")
        module.classes.append(
            GeneratedClass(
                name="Foo",
                fields=[
                    FieldDef(
                        python_name="value",
                        type_str="str",
                        json_name="value",
                        is_required=True,
                    )
                ],
            )
        )
        result = module.render()
        assert "class Foo:" in result
        assert "from dataclasses import dataclass" in result

    def test_deduplicates_classes(self) -> None:
        module = ModuleCode(schema_url="http://test")
        module.classes.append(
            GeneratedClass(
                name="Foo",
                fields=[
                    FieldDef(
                        python_name="a", type_str="str", json_name="a", is_required=True
                    )
                ],
            )
        )
        module.classes.append(
            GeneratedClass(
                name="Foo",
                fields=[
                    FieldDef(
                        python_name="b",
                        type_str="int",
                        json_name="b",
                        is_required=False,
                    )
                ],
            )
        )
        result = module.render()
        assert result.count("class Foo:") == 1
        assert "a: str" in result
        assert "b: int" in result

    def test_renders_imports(self) -> None:
        module = ModuleCode(schema_url="http://test")
        module.imports.append(
            ImportEntry(
                module="allotropy.allotrope.models.adm.core.rec._2024._09.core",
                name="TQuantityValue",
            )
        )
        module.classes.append(
            GeneratedClass(
                name="Foo",
                fields=[
                    FieldDef(
                        python_name="value",
                        type_str="TQuantityValue",
                        json_name="value",
                        is_required=True,
                    )
                ],
                dependencies={"TQuantityValue"},
            )
        )
        result = module.render()
        assert (
            "from allotropy.allotrope.models.adm.core.rec._2024._09.core import TQuantityValue"
            in result
        )

    def test_reexport_syntax(self) -> None:
        module = ModuleCode(schema_url="http://test")
        module.imports.append(
            ImportEntry(
                module="allotropy.allotrope.models.shared.definitions.definitions",
                name="TQuantityValue",
                reexport=True,
            )
        )
        module.classes.append(
            GeneratedClass(
                name="Foo",
                fields=[],
            )
        )
        result = module.render()
        assert "TQuantityValue as TQuantityValue" in result

    def test_skips_local_class_imports(self) -> None:
        module = ModuleCode(schema_url="http://test")
        module.imports.append(ImportEntry(module="allotropy.some.module", name="Foo"))
        module.classes.append(
            GeneratedClass(
                name="Foo",
                fields=[],
            )
        )
        result = module.render()
        # Should NOT import Foo since it's defined locally
        assert "from allotropy.some.module import Foo" not in result

    def test_detects_enum_import(self) -> None:
        module = ModuleCode(schema_url="http://test")
        module.classes.append(
            GeneratedClass(
                name="MyEnum",
                enum_members=[("value_a", "a")],
            )
        )
        result = module.render()
        assert "from enum import Enum" in result

    def test_detects_literal_import(self) -> None:
        module = ModuleCode(schema_url="http://test")
        module.classes.append(
            GeneratedClass(
                name="MyLiteral",
                alias_target='Literal["a"]',
            )
        )
        result = module.render()
        assert "from typing import Literal" in result

    def test_type_alias_no_dataclass_import(self) -> None:
        module = ModuleCode(schema_url="http://test")
        module.classes.append(
            GeneratedClass(
                name="MyAlias",
                alias_target="str | int",
            )
        )
        result = module.render()
        assert "from dataclasses import" not in result


# ---------------------------------------------------------------------------
# SchemaCodeGenerator — enum generation
# ---------------------------------------------------------------------------


def _make_generator(
    schemas: dict[str, dict[str, Any]],
    urls: list[str] | None = None,
) -> SchemaCodeGenerator:
    """Create a SchemaCodeGenerator with given schemas."""
    if urls is None:
        urls = list(schemas.keys())
    return SchemaCodeGenerator(schemas, urls, "allotropy.allotrope.models")


class TestSchemaCodeGeneratorEnum:
    def test_generate_enum_class(self) -> None:
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "containerType": {
                        "enum": ["well plate", "tube", "reactor"],
                    }
                }
            }
        }
        gen = _make_generator(schemas)
        ModuleCode(schema_url=schema_url)
        cls = gen._generate_enum(
            "ContainerType", {"enum": ["well plate", "tube", "reactor"]}
        )
        code = cls.render()
        assert "class ContainerType(Enum):" in code
        assert 'well_plate = "well plate"' in code
        assert 'tube = "tube"' in code
        assert 'reactor = "reactor"' in code

    def test_generate_enum_single_value(self) -> None:
        # Single-value enums should remain Literal in the property resolver,
        # but _generate_enum itself always produces Enum class
        gen = _make_generator({})
        cls = gen._generate_enum("SingleValue", {"enum": ["only"]})
        code = cls.render()
        assert "class SingleValue(Enum):" in code
        assert 'only = "only"' in code


class TestSchemaCodeGeneratorJsonTypeToPython:
    def test_string(self) -> None:
        gen = _make_generator({})
        assert gen._json_type_to_python("string") == "str"

    def test_integer(self) -> None:
        gen = _make_generator({})
        assert gen._json_type_to_python("integer") == "int"

    def test_number(self) -> None:
        gen = _make_generator({})
        assert gen._json_type_to_python("number") == "float"

    def test_boolean(self) -> None:
        gen = _make_generator({})
        assert gen._json_type_to_python("boolean") == "bool"

    def test_array_of_strings(self) -> None:
        gen = _make_generator({})
        result = gen._json_type_to_python(["string", "null"])
        assert "str" in result


# ---------------------------------------------------------------------------
# SchemaCodeGenerator — full module generation
# ---------------------------------------------------------------------------


class TestSchemaCodeGeneratorGenerate:
    """Integration-level tests using minimal schema fixtures."""

    def test_simple_object_schema(self) -> None:
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "simpleDocument": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "count": {"type": "integer"},
                        },
                        "required": ["name"],
                    }
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        assert "class SimpleDocument:" in source
        assert "name: str" in source
        assert "count: int | None" in source

    def test_ref_between_schemas(self) -> None:
        base_url = f"{BASE}adm/core/REC/2024/09/core.schema"
        tech_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            base_url: {
                "$defs": {
                    "baseType": {
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                        "required": ["value"],
                    }
                }
            },
            tech_url: {
                "$defs": {
                    "techType": {
                        "type": "object",
                        "properties": {
                            "base": {"$ref": f"{base_url}#/$defs/baseType"},
                        },
                        "required": ["base"],
                    }
                }
            },
        }
        gen = _make_generator(schemas, [base_url, tech_url])
        modules = gen.generate_all()
        tech_source = modules[tech_url].render()
        assert "BaseType" in tech_source
        assert "import" in tech_source

    def test_type_alias_for_ref(self) -> None:
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "baseType": {
                        "type": "object",
                        "properties": {"x": {"type": "string"}},
                        "required": ["x"],
                    },
                    "aliasType": {
                        "$ref": "#/$defs/baseType",
                    },
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        assert "AliasType = BaseType" in source

    def test_array_type_alias(self) -> None:
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "itemType": {
                        "type": "object",
                        "properties": {"v": {"type": "string"}},
                        "required": ["v"],
                    },
                    "itemList": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/itemType"},
                    },
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        assert "list[ItemType]" in source

    def test_enum_inline_on_property(self) -> None:
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "myDoc": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "enum": ["active", "inactive", "pending"],
                            },
                        },
                    }
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        # Multi-value enum should produce an Enum class
        assert "class Status(Enum):" in source
        assert 'active = "active"' in source

    def test_single_value_enum_produces_literal(self) -> None:
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "myDoc": {
                        "type": "object",
                        "properties": {
                            "fixed_type": {
                                "enum": ["only_value"],
                            },
                        },
                    }
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        assert 'Literal["only_value"]' in source

    def test_one_of_produces_union(self) -> None:
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "typeA": {
                        "type": "object",
                        "properties": {"a": {"type": "string"}},
                        "required": ["a"],
                    },
                    "typeB": {
                        "type": "object",
                        "properties": {"b": {"type": "integer"}},
                        "required": ["b"],
                    },
                    "unionDef": {
                        "oneOf": [
                            {"$ref": "#/$defs/typeA"},
                            {"$ref": "#/$defs/typeB"},
                        ]
                    },
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        assert "TypeA" in source
        assert "TypeB" in source
        assert "UnionDef = " in source

    def test_anyof_produces_union(self) -> None:
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "optA": {
                        "type": "object",
                        "properties": {"a": {"type": "string"}},
                        "required": ["a"],
                    },
                    "optB": {
                        "type": "object",
                        "properties": {"b": {"type": "integer"}},
                        "required": ["b"],
                    },
                    "anyDef": {
                        "anyOf": [
                            {"$ref": "#/$defs/optA"},
                            {"$ref": "#/$defs/optB"},
                        ]
                    },
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        assert "AnyDef = " in source

    def test_allof_inheritance(self) -> None:
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "parentType": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                    "childType": {
                        "allOf": [
                            {"$ref": "#/$defs/parentType"},
                            {
                                "type": "object",
                                "properties": {"extra": {"type": "integer"}},
                            },
                        ]
                    },
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        assert "class ChildType(ParentType):" in source
        assert "extra: int" in source

    def test_constraint_only_property_skipped(self) -> None:
        """Properties with only validation keywords (minItems, etc.) should be skipped."""
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "myDoc": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "items_constraint": {"minItems": 1, "maxItems": 10},
                        },
                        "required": ["name"],
                    }
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        assert "name: str" in source
        assert "items_constraint" not in source

    def test_asm_metadata_properties_skipped(self) -> None:
        """Properties starting with $asm. or $schema are metadata, not fields."""
        schema_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas = {
            schema_url: {
                "$defs": {
                    "myDoc": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "$schema": {"type": "string"},
                            "$id": {"type": "string"},
                        },
                        "required": ["name"],
                    }
                }
            }
        }
        gen = _make_generator(schemas)
        modules = gen.generate_all()
        source = modules[schema_url].render()
        assert "name: str" in source
        # $schema and $id are metadata, should be skipped
        assert "field_schema" not in source
        assert "field_id" not in source


# ---------------------------------------------------------------------------
# GeneratedClass — validation and render variants
# ---------------------------------------------------------------------------


class TestGeneratedClassValidation:
    def test_rejects_multiple_variants(self) -> None:
        with pytest.raises(ValueError, match="multiple variants"):
            GeneratedClass(
                name="Bad",
                fields=[],
                enum_members=[("a", "a")],
            )

    def test_rejects_alias_with_fields(self) -> None:
        with pytest.raises(ValueError, match="multiple variants"):
            GeneratedClass(
                name="Bad",
                fields=[],
                alias_target="str",
            )

    def test_allows_single_variant(self) -> None:
        # Should not raise
        GeneratedClass(name="Ok", fields=[])
        GeneratedClass(name="Ok", enum_members=[("a", "a")])
        GeneratedClass(name="Ok", alias_target="str")

    def test_allows_no_variant(self) -> None:
        # None populated = default dataclass (fields=None renders as pass)
        cls = GeneratedClass(name="Empty")
        assert "pass" in cls.render()


class TestGeneratedClassRender:
    def test_renders_type_alias(self) -> None:
        cls = GeneratedClass(name="MyAlias", alias_target="str | int")
        assert cls.render() == "MyAlias = str | int"

    def test_renders_enum(self) -> None:
        cls = GeneratedClass(
            name="Color",
            enum_members=[("red", "red"), ("blue", "blue")],
        )
        code = cls.render()
        assert "class Color(Enum):" in code
        assert '    red = "red"' in code
        assert '    blue = "blue"' in code

    def test_renders_empty_dataclass(self) -> None:
        cls = GeneratedClass(name="Empty", fields=[])
        code = cls.render()
        assert "@dataclass(frozen=True, kw_only=True)" in code
        assert "class Empty:" in code
        assert "    pass" in code

    def test_renders_dataclass_with_bases(self) -> None:
        cls = GeneratedClass(
            name="Child",
            fields=[
                FieldDef(
                    python_name="extra",
                    type_str="int",
                    json_name="extra",
                    is_required=False,
                )
            ],
            bases=["Parent"],
            dependencies={"Parent"},
        )
        code = cls.render()
        assert "class Child(Parent):" in code
        assert "extra: int | None = None" in code

    def test_renders_non_frozen_dataclass(self) -> None:
        cls = GeneratedClass(
            name="Model",
            fields=[
                FieldDef(
                    python_name="name",
                    type_str="str",
                    json_name="name",
                    is_required=True,
                )
            ],
            frozen=False,
        )
        code = cls.render()
        assert "@dataclass(kw_only=True)" in code
        assert "frozen" not in code

    def test_required_fields_before_optional(self) -> None:
        cls = GeneratedClass(
            name="Doc",
            fields=[
                FieldDef(
                    python_name="opt",
                    type_str="str",
                    json_name="opt",
                    is_required=False,
                ),
                FieldDef(
                    python_name="req", type_str="str", json_name="req", is_required=True
                ),
            ],
        )
        code = cls.render()
        lines = code.split("\n")
        field_lines = [
            line
            for line in lines
            if ": " in line and not line.strip().startswith(("class", "@"))
        ]
        assert "req: str" in field_lines[0]
        assert "opt: str | None = None" in field_lines[1]

    def test_json_name_metadata_when_needed(self) -> None:
        cls = GeneratedClass(
            name="Doc",
            fields=[
                FieldDef(
                    python_name="p_co2",
                    type_str="float",
                    json_name="pCO2",
                    is_required=True,
                ),
            ],
        )
        code = cls.render()
        assert '"pCO2"' in code
        assert "field(metadata=" in code

    def test_no_json_name_metadata_for_trivial(self) -> None:
        cls = GeneratedClass(
            name="Doc",
            fields=[
                FieldDef(
                    python_name="device_type",
                    type_str="str",
                    json_name="device type",
                    is_required=True,
                ),
            ],
        )
        code = cls.render()
        assert "device_type: str" in code
        assert "field(" not in code


class TestGeneratedClassCopy:
    def test_copy_is_independent(self) -> None:
        original = GeneratedClass(
            name="Foo",
            fields=[
                FieldDef(
                    python_name="a", type_str="str", json_name="a", is_required=True
                )
            ],
            bases=["Base"],
            dependencies={"Base"},
        )
        copied = original.copy()
        # Modify the copy
        assert copied.fields is not None
        copied.fields.append(
            FieldDef(python_name="b", type_str="int", json_name="b", is_required=False)
        )
        copied.bases.append("Other")
        copied.dependencies.add("Other")
        # Original should be unchanged
        assert original.fields is not None
        assert len(original.fields) == 1
        assert len(original.bases) == 1
        assert original.dependencies == {"Base"}

    def test_copy_enum(self) -> None:
        original = GeneratedClass(
            name="Color",
            enum_members=[("red", "red")],
        )
        copied = original.copy()
        assert copied.enum_members is not None
        copied.enum_members.append(("blue", "blue"))
        assert original.enum_members is not None
        assert len(original.enum_members) == 1

    def test_copy_alias(self) -> None:
        original = GeneratedClass(name="Alias", alias_target="str | int")
        copied = original.copy()
        assert copied.alias_target == "str | int"
        assert copied.name == "Alias"


# ---------------------------------------------------------------------------
# QuantityValueManager
# ---------------------------------------------------------------------------


class TestQuantityValueManager:
    def test_get_or_create_new(self) -> None:
        mgr = QuantityValueManager()
        result = mgr.get_or_create("mAU")
        assert result == "TQuantityValueMAU"
        assert ("TQuantityValueMAU", "mAU") in mgr.new_classes

    def test_get_or_create_idempotent(self) -> None:
        mgr = QuantityValueManager()
        first = mgr.get_or_create("nm")
        second = mgr.get_or_create("nm")
        assert first == second
        assert len(mgr.new_classes) == 1

    def test_existing_classes_not_recorded_as_new(self) -> None:
        mgr = QuantityValueManager(existing_classes={"TQuantityValueDegC"})
        result = mgr.get_or_create("°C")
        assert result == "TQuantityValueDegC"
        assert len(mgr.new_classes) == 0

    def test_different_units_produce_different_classes(self) -> None:
        mgr = QuantityValueManager()
        a = mgr.get_or_create("mAU")
        b = mgr.get_or_create("nm")
        assert a != b
        assert len(mgr.new_classes) == 2


# ---------------------------------------------------------------------------
# SchemaMerger
# ---------------------------------------------------------------------------


class TestSchemaMerger:
    def test_resolve_ref_to_local_def(self) -> None:
        url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas: dict[str, Any] = {
            url: {
                "$defs": {
                    "myType": {
                        "type": "object",
                        "properties": {"x": {"type": "string"}},
                    }
                }
            }
        }
        merger = SchemaMerger(schemas)
        result = merger.resolve_ref_to_schema(url, f"{url}#/$defs/myType")
        assert result is not None
        assert "properties" in result
        assert "x" in result["properties"]

    def test_resolve_ref_to_external_def(self) -> None:
        core_url = f"{BASE}adm/core/REC/2024/09/core.schema"
        tech_url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas: dict[str, Any] = {
            core_url: {
                "$defs": {"baseType": {"type": "object", "properties": {"v": {}}}}
            },
            tech_url: {"$defs": {}},
        }
        merger = SchemaMerger(schemas)
        result = merger.resolve_ref_to_schema(tech_url, f"{core_url}#/$defs/baseType")
        assert result is not None
        assert "v" in result["properties"]

    def test_resolve_ref_missing_returns_none(self) -> None:
        merger = SchemaMerger({})
        result = merger.resolve_ref_to_schema("http://x", "#/$defs/missing")
        assert result is None

    def test_merge_any_of_variants_into_props(self) -> None:
        url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas: dict[str, Any] = {
            url: {
                "$defs": {
                    "variantA": {
                        "type": "object",
                        "properties": {
                            "shared": {"type": "string"},
                            "only_a": {"type": "integer"},
                        },
                        "required": ["shared", "only_a"],
                    },
                    "variantB": {
                        "type": "object",
                        "properties": {
                            "shared": {"type": "string"},
                            "only_b": {"type": "boolean"},
                        },
                        "required": ["shared", "only_b"],
                    },
                }
            }
        }
        merger = SchemaMerger(schemas)
        merged_props: dict[str, Any] = {}
        merger.merge_any_of_variants_into_props(
            url,
            [
                {"$ref": f"{url}#/$defs/variantA"},
                {"$ref": f"{url}#/$defs/variantB"},
            ],
            merged_props,
        )
        # All properties from both variants should be present
        assert "shared" in merged_props
        assert "only_a" in merged_props
        assert "only_b" in merged_props

    def test_merge_variant_properties(self) -> None:
        url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas: dict[str, Any] = {
            url: {
                "$defs": {
                    "det": {
                        "type": "object",
                        "properties": {
                            "field_a": {"type": "string"},
                        },
                    }
                }
            }
        }
        merger = SchemaMerger(schemas)
        merged: dict[str, Any] = {"existing": {"type": "integer"}}
        merger.merge_variant_properties(url, [{"$ref": f"{url}#/$defs/det"}], merged)
        assert "existing" in merged
        assert "field_a" in merged

    def test_deep_nesting_warns(self) -> None:
        url = f"{BASE}adm/test/REC/2024/09/test.schema"
        schemas: dict[str, Any] = {
            url: {
                "$defs": {
                    "outer": {
                        "type": "object",
                        "properties": {"x": {"type": "string"}},
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {"y": {"type": "string"}},
                                "anyOf": [{"properties": {"z": {"type": "string"}}}],
                            }
                        ],
                    }
                }
            }
        }
        merger = SchemaMerger(schemas)
        merged: dict[str, Any] = {}
        with pytest.warns(UserWarning, match="3\\+ levels"):
            merger.merge_variant_properties(
                url, [{"$ref": f"{url}#/$defs/outer"}], merged
            )
