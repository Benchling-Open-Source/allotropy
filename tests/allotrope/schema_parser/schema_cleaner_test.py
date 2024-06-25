import re
from typing import Any

from deepdiff import DeepDiff
import pytest

from allotropy.allotrope.schema_parser.schema_cleaner import (
    _powerset_indices_from_index,
    SchemaCleaner,
)


def validate_cleaned_schema(
    schema: dict[str, Any],
    expected: dict[str, Any],
    *,
    test_defs: bool | None = False,
) -> SchemaCleaner:
    # Add $defs/<core schema>/$defs/tQuantityValue as it is used for many tests.
    if "$defs" not in schema:
        schema["$defs"] = {}
    if (
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema"
        not in schema["$defs"]
    ):
        schema["$defs"][
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema"
        ] = {"$defs": {}}
    schema["$defs"][
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema"
    ]["$defs"]["tQuantityValue"] = {
        "type": "object",
        "properties": {
            "value": {
                "oneOf": [
                    {"type": "number"},
                    {"enum": ["NaN", "+Infinity", "-Infinity"]},
                ]
            },
            "unit": {"$ref": "#/$defs/tUnit"},
            "has statistic datum role": {"$ref": "#/$defs/tStatisticDatumRole"},
            "@type": {"$ref": "#/$defs/tClass"},
        },
        "$asm.type": "http://qudt.org/schema/qudt#QuantityValue",
        "required": ["value", "unit"],
    }
    schema_cleaner = SchemaCleaner()
    actual = schema_cleaner.clean(schema)

    if not test_defs:
        actual.pop("$defs", None)
        expected.pop("$defs", None)

    # print(DeepDiff(expected, actual, exclude_regex_paths=exclude_regex))
    assert not DeepDiff(
        expected,
        actual,
    )

    return schema_cleaner


def test_clean_http_refs() -> None:
    defs_schema = {
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema": {
            "$defs": {
                "orderedItem": {"properties": {"key": "value"}},
                "tNumberArray": {"properties": {"key": "value"}},
            }
        }
    }
    schema = {
        "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/orderedItem",
        "$defs": defs_schema,
    }
    validate_cleaned_schema(
        schema, {"$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/orderedItem"}
    )

    allof_schema = {
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/orderedItem"
            },
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tNumberArray"
            },
        ],
        "$defs": defs_schema,
    }
    validate_cleaned_schema(
        allof_schema,
        {
            "allOf": [
                {"$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/orderedItem"},
                {"$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/tNumberArray"},
            ]
        },
    )


def test_fix_quantity_value_reference() -> None:
    schema = {
        "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001233",
        "$asm.pattern": "quantity datum",
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tQuantityValue"
            },
            {
                "$ref": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema#/$defs/(unitless)"
            },
        ],
    }
    validate_cleaned_schema(
        schema,
        {
            "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001233",
            "$asm.pattern": "quantity datum",
            "$ref": "#/$defs/tQuantityValueUnitless",
        },
    )


def test_add_missing_unit() -> None:
    schema = {
        "properties": {
            "$ref": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema#/$defs/10%5E7%20fakes~1mL"
        },
        "$defs": {
            "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema": {
                "$id": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema",
                "$comment": "Auto-generated from QUDT 1.1 and Allotrope Extensions for QUDT",
                "$defs": {
                    "10^7 fakes/mL": {
                        "properties": {
                            "unit": {
                                "type": "string",
                                "const": "10^7 fakes/mL",
                                "$asm.unit-iri": "http://purl.allotrope.org/ontology/qudt-ext/unit#FakeUnit",
                            }
                        },
                        "required": ["unit"],
                    }
                },
            }
        },
    }
    schema_cleaner = validate_cleaned_schema(
        schema,
        {
            "properties": {"$ref": "#/$defs/FakeUnit"},
        },
    )
    assert schema_cleaner.get_referenced_units() == {
        "10^7 fakes/mL": "http://purl.allotrope.org/ontology/qudt-ext/unit#FakeUnit"
    }


def test_fix_quantity_value_reference_add_missing_unit() -> None:
    schema = {
        "properties": {
            "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001233",
            "$asm.pattern": "quantity datum",
            "allOf": [
                {
                    "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tQuantityValue"
                },
                {
                    "$ref": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema#/$defs/fake-unit"
                },
            ],
        },
        "$defs": {
            "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema": {
                "$id": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema",
                "$comment": "Auto-generated from QUDT 1.1 and Allotrope Extensions for QUDT",
                "$defs": {
                    "fake-unit": {
                        "properties": {
                            "unit": {
                                "type": "string",
                                "const": "fake-unit",
                                "$asm.unit-iri": "http://purl.allotrope.org/ontology/qudt-ext/unit#FakeUnit",
                            }
                        },
                        "required": ["unit"],
                    }
                },
            },
        },
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {
                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001233",
                "$asm.pattern": "quantity datum",
                "$ref": "#/$defs/tQuantityValueFakeUnit",
            }
        },
    )


def test_fix_quantity_value_reference_after_oneof_nested_in_allof() -> None:
    schema = {
        "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001180",
        "$asm.pattern": "quantity datum",
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tQuantityValue"
            },
            {
                "oneOf": [
                    {
                        "$ref": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema#/$defs/ms"
                    },
                    {
                        "$ref": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema#/$defs/%"
                    },
                ]
            },
        ],
    }
    validate_cleaned_schema(
        schema,
        {
            "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001180",
            "$asm.pattern": "quantity datum",
            "oneOf": [
                {"$ref": "#/$defs/tQuantityValueMilliSecond"},
                {"$ref": "#/$defs/tQuantityValuePercent"},
            ],
        },
    )


def test_replace_definiton() -> None:
    # tQuantityValue in core.schema matches the schema of tQuantityValue in shared/definitions.json, so the
    # ref will be replaced by that, and tQuantityValue will be removed from cleaned defs.
    # asm is not in shared/definitions, so it will be preserved.
    schema = {
        "properties": {
            "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001180",
            "$asm.pattern": "quantity datum",
            "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tQuantityValue",
        },
        "$defs": {
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema": {
                "$id": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema",
                "title": "Schema for leaf node values.",
                "$defs": {
                    "asm": {
                        "properties": {
                            "$asm.manifest": {
                                "oneOf": [
                                    {"type": "string", "format": "iri"},
                                    {
                                        "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/manifest.schema"
                                    },
                                ]
                            }
                        }
                    },
                },
            }
        },
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {
                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001180",
                "$asm.pattern": "quantity datum",
                "$ref": "#/$defs/tQuantityValue",
            },
            "$defs": {
                "adm_core_REC_2023_09_core_schema": {
                    "$defs": {
                        "asm": {
                            "properties": {
                                "$asm.manifest": {
                                    "oneOf": [
                                        {"type": "string", "format": "iri"},
                                        {
                                            "$ref": "#/$defs/adm_core_REC_2023_09_manifest_schema"
                                        },
                                    ]
                                }
                            }
                        }
                    }
                }
            },
        },
        test_defs=True,
    )


def test_fix_nested_def_references() -> None:
    # References to definitions inside of a definiton schema do not use the full path, making it impossible
    # for the generation script to find them. Fix this by replacing the def with the correct path.
    # e.g. a #/$defs/nestedSchema inside of core_schema will become #/$defs/core_schema/$defs/nestedSchema
    schema = {
        "$defs": {
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/hierarchy.schema": {
                "$defs": {
                    "anotherThing": {
                        "properties": {
                            "allOf": [
                                {
                                    "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tQuantityValue"
                                },
                                {
                                    "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/nestedSchema"
                                },
                            ]
                        }
                    }
                }
            },
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema": {
                "$id": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema",
                "title": "Schema for leaf node values.",
                "$defs": {
                    "aThing": {
                        "properties": {
                            "allOf": [
                                {"$ref": "#/$defs/nestedSchema"},
                                {"$ref": "#/$defs/otherSchema"},
                                {"$ref": "#/$defs/tQuantityValue"},
                            ]
                        }
                    },
                    "nestedSchema": {"properties": {"type": "string"}},
                },
            },
            "otherSchema": {
                "properties": {
                    "key": "string",
                }
            },
        }
    }
    validate_cleaned_schema(
        schema,
        {
            "$defs": {
                "adm_core_REC_2023_09_hierarchy_schema": {
                    "$defs": {
                        "anotherThing": {
                            "properties": {
                                "allOf": [
                                    {"$ref": "#/$defs/tQuantityValue"},
                                    {
                                        "$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/nestedSchema"
                                    },
                                ]
                            }
                        }
                    }
                },
                "adm_core_REC_2023_09_core_schema": {
                    "$defs": {
                        "aThing": {
                            "properties": {
                                "allOf": [
                                    {
                                        "$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/nestedSchema"
                                    },
                                    {"$ref": "#/$defs/otherSchema"},
                                    {"$ref": "#/$defs/tQuantityValue"},
                                ]
                            }
                        },
                        "nestedSchema": {"properties": {"type": "string"}},
                    }
                },
                "otherSchema": {
                    "properties": {
                        "key": "string",
                    }
                },
            }
        },
        test_defs=True,
    )


def test_singular_anyof() -> None:
    schema = {
        "anyOf": [
            {
                "items": {"properties": {"key1": "value"}},
            }
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "items": {
                "properties": {
                    "key1": "value",
                }
            },
        },
    )


def test_combine_anyof_non_conflicting_optional_keys() -> None:
    schema = {
        "anyOf": [
            {"properties": {"key1": "value"}},
            {"properties": {"key2": "value"}},
            {"properties": {"key3": "value"}},
        ]
    }
    validate_cleaned_schema(
        schema, {"properties": {"key1": "value", "key2": "value", "key3": "value"}}
    )


def test_combine_anyof_with_conflicting_keys() -> None:
    schema = {
        "anyOf": [
            {"properties": {"key1": "value", "key2": "value"}},
            {"properties": {"key1": "otherValue", "key3": "value"}},
            {"properties": {"key4": "value"}},
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {
                    "properties": {
                        "key1": "otherValue",
                        "key3": "value",
                        "key4": "value",
                    }
                },
                {
                    "properties": {
                        "key1": "value",
                        "key2": "value",
                        "key4": "value",
                    }
                },
            ]
        },
    )


def test_combine_anyof_with_multiple_conflicting_keys() -> None:
    schema = {
        "anyOf": [
            {"properties": {"key1": "value", "key2": "value"}},
            {"properties": {"key1": "otherValue", "key2": "otherValue"}},
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {"properties": {"key1": "otherValue", "key2": "otherValue"}},
                {"properties": {"key1": "value", "key2": "value"}},
            ]
        },
    )


def test_combine_anyof_with_nested_conflicting_keys() -> None:
    schema = {
        "anyOf": [
            {
                "properties": {
                    "obj1": {"properties": {"key1": "string"}},
                    "field1": "value",
                }
            },
            {
                "properties": {
                    "obj1": {"properties": {"key1": "boolean"}},
                }
            },
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {
                    "properties": {
                        "obj1": {"properties": {"key1": "boolean"}},
                    }
                },
                {
                    "properties": {
                        "obj1": {"properties": {"key1": "string"}},
                        "field1": "value",
                    }
                },
            ]
        },
    )


def test_combine_anyof_with_nested_anyof() -> None:
    schema = {
        "anyOf": [
            {
                "properties": {
                    "obj1": {
                        "anyOf": [
                            {"properties": {"key1": "value"}},
                            {"properties": {"key2": "value"}},
                        ]
                    }
                }
            },
            {
                "properties": {
                    "obj1": {
                        "anyOf": [
                            {"properties": {"key3": "value"}},
                            {"properties": {"key4": "value"}},
                        ]
                    }
                }
            },
        ]
    }
    # NOTE: because there are no conflicting required keys, all schemas are combined into a single schema.
    validate_cleaned_schema(
        schema,
        {
            "properties": {
                "obj1": {
                    "allOf": [
                        {"properties": {"key1": "value", "key2": "value"}},
                        {"properties": {"key3": "value", "key4": "value"}},
                    ]
                }
            }
        },
    )


def test_combine_anyof_with_required_values() -> None:
    schema = {
        "anyOf": [
            {
                "items": {"properties": {"key1": "value"}, "required": ["key1"]},
                "minItems": 0,
            },
            {"items": {"properties": {"key2": "value"}}, "minItems": 0},
            {"items": {"properties": {"key3": "value"}}, "minItems": 0},
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {
                    "items": {
                        "properties": {
                            "key1": "value",
                            "key2": "value",
                            "key3": "value",
                        },
                        "required": ["key1"],
                    },
                },
                {
                    "items": {"properties": {"key2": "value", "key3": "value"}},
                },
            ]
        },
    )


def test_combine_anyof_with_multiple_required_values() -> None:
    schema = {
        "anyOf": [
            {
                "properties": {"key1": "value", "key2": "value"},
                "required": ["key1", "key2"],
            },
            {"properties": {"key3": "value"}},
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {
                    "properties": {"key1": "value", "key2": "value", "key3": "value"},
                    "required": ["key1", "key2"],
                },
                {"properties": {"key3": "value"}},
            ]
        },
    )


def test_combine_anyof_with_multiple_required_value_sets() -> None:
    schema = {
        "anyOf": [
            {
                "properties": {"key1": "value", "key2": "value", "key3": "value"},
                "required": ["key1", "key2"],
            },
            {"properties": {"key2": "value", "key3": "value"}},
            {"properties": {"key4": "value"}, "required": ["key4"]},
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {
                    "properties": {
                        "key1": "value",
                        "key2": "value",
                        "key3": "value",
                        "key4": "value",
                    },
                    "required": ["key1", "key2", "key4"],
                },
                {
                    "properties": {"key2": "value", "key3": "value", "key4": "value"},
                    "required": ["key4"],
                },
                {
                    "properties": {"key1": "value", "key2": "value", "key3": "value"},
                    "required": ["key1", "key2"],
                },
                {"properties": {"key2": "value", "key3": "value"}},
            ]
        },
    )


def test_combine_anyof_with_parent_object() -> None:
    schema = {
        "items": {
            "properties": {"parentKey": "value"},
            "anyOf": [
                {"properties": {"key1": "value"}},
                {"properties": {"key2": "value"}},
            ],
        },
        "minItems": 1,
    }
    validate_cleaned_schema(
        schema,
        {
            "items": {
                "allOf": [
                    {"properties": {"parentKey": "value"}},
                    {"properties": {"key1": "value", "key2": "value"}},
                ]
            },
        },
    )


def test_combine_anyof_with_parent_object_with_required_keys() -> None:
    schema = {
        "properties": {
            "parentKey": "value",
        },
        "required": ["parentKey"],
        "anyOf": [
            {
                "properties": {"childKey": "value"},
            },
        ],
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {"parentKey": "value", "childKey": "value"},
            "required": ["parentKey"],
        },
    )


def test_combine_anyof_with_parent_object_with_child_required_keys() -> None:
    schema = {
        "properties": {
            "parentKey": "value",
        },
        "required": ["parentKey"],
        "anyOf": [
            {
                "properties": {"childKey1": "value"},
            },
            {
                "properties": {"childKey2": "value"},
                "required": ["childKey2"],
            },
        ],
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {
                    "properties": {
                        "parentKey": "value",
                        "childKey1": "value",
                        "childKey2": "value",
                    },
                    "required": ["childKey2", "parentKey"],
                },
                {
                    "properties": {
                        "parentKey": "value",
                        "childKey1": "value",
                    },
                    "required": ["parentKey"],
                },
            ]
        },
    )


def test_combine_anyof_with_parent_anyof_required_keys() -> None:
    schema = {
        "properties": {
            "key1": "value",
            "key2": "otherValue",
        },
        "anyOf": [
            {"required": ["key1"]},
            {"required": ["key2"]},
        ],
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {
                    "properties": {"key1": "value", "key2": "otherValue"},
                    "required": ["key1", "key2"],
                },
                {
                    "properties": {"key1": "value", "key2": "otherValue"},
                    "required": ["key1"],
                },
                {
                    "properties": {"key1": "value", "key2": "otherValue"},
                    "required": ["key2"],
                },
            ]
        },
    )


def test_fixes_singlular_allof() -> None:
    schema = {
        "allOf": [{"key": "value"}],
    }
    validate_cleaned_schema(schema, {"key": "value"})


def test_fixes_oneof_nested_in_allof() -> None:
    schema = {
        "allOf": [
            {"properties": {"key1": "value1"}},
            {
                "oneOf": [
                    {"properties": {"key2": "value2"}},
                    {"properties": {"key3": "value3"}},
                ]
            },
        ]
    }
    expected = {
        "oneOf": [
            {
                "allOf": [
                    {"properties": {"key1": "value1"}},
                    {"properties": {"key2": "value2"}},
                ]
            },
            {
                "allOf": [
                    {"properties": {"key1": "value1"}},
                    {"properties": {"key3": "value3"}},
                ]
            },
        ]
    }
    validate_cleaned_schema(schema, expected)

    # Flip so oneOf is first in allOf list, to cover all branches.
    schema["allOf"] = schema["allOf"][::-1]
    expected["oneOf"] = [{"allOf": value["allOf"][::-1]} for value in expected["oneOf"]]
    validate_cleaned_schema(schema, expected)


def test_fixes_oneof_nested_in_allof_in_reference() -> None:
    schema = {
        "allOf": [{"properties": {"key1": "value1"}}, {"$ref": "#/$defs/oneOfSchema"}],
        "$defs": {
            "oneOfSchema": {
                "oneOf": [
                    {"properties": {"key2": "value2"}},
                    {"properties": {"key3": "value3"}},
                ]
            }
        },
    }
    expected = {
        "oneOf": [
            {
                "allOf": [
                    {"properties": {"key1": "value1"}},
                    {"properties": {"key2": "value2"}},
                ]
            },
            {
                "allOf": [
                    {"properties": {"key1": "value1"}},
                    {"properties": {"key3": "value3"}},
                ]
            },
        ]
    }
    validate_cleaned_schema(schema, expected)


def test_combine_allof() -> None:
    schema = {
        "allOf": [
            {"properties": {"key1": "value"}, "required": ["key1"]},
            {"properties": {"key2": "value"}},
            {"properties": {"key3": "otherValue"}},
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {"key1": "value", "key2": "value", "key3": "otherValue"},
            "required": ["key1"],
        },
    )


def test_combine_allof_empty_object_schema() -> None:
    # Sometimes ASM only specifies the $asm properties, in this case we should successfully combine.
    schema = {
        "allOf": [
            {
                "type": "object",
                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002655",
                "$asm.pattern": "aggregate datum",
            },
            {
                "type": "object",
                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002655",
                "$asm.pattern": "aggregate datum",
                "properties": {"key1": "value"},
                "required": ["key1"],
            },
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {"key1": "value"},
            "required": ["key1"],
        },
    )


def test_combine_allof_all_same_value() -> None:
    schemas = [
        {
            "oneOf": [
                {"$ref": "#/$defs/tQuantityValueSecondTime"},
                {"$ref": "#/$defs/tQuantityValueMilliliter"},
            ]
        },
        {
            "oneOf": [
                {"$ref": "#/$defs/tQuantityValueSecondTime"},
                {"$ref": "#/$defs/tQuantityValueMilliliter"},
            ]
        },
        {
            "oneOf": [
                {"$ref": "#/$defs/tQuantityValueSecondTime"},
                {"$ref": "#/$defs/tQuantityValueMilliliter"},
            ]
        },
    ]

    assert SchemaCleaner()._combine_allof(schemas) == {
        "oneOf": [
            {"$ref": "#/$defs/tQuantityValueSecondTime"},
            {"$ref": "#/$defs/tQuantityValueMilliliter"},
        ]
    }


def test_combine_allof_key_with_matching_value() -> None:
    schema = {
        "allOf": [
            {"properties": {"key1": "value"}, "required": ["key1"]},
            {"properties": {"key1": "value", "key2": "value"}},
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {
                "key1": "value",
                "key2": "value",
            },
            "required": ["key1"],
        },
    )


def test_combine_allof_fails_on_conflicting_key() -> None:
    schema = {
        "allOf": [
            {"properties": {"key1": "value"}, "required": ["key1"]},
            {"properties": {"key1": "otherValue"}},
        ]
    }
    with pytest.raises(
        AssertionError,
        match=re.escape(
            "Error combining schemas, conflicting values for key 'key1': ['value', 'otherValue']"
        ),
    ):
        SchemaCleaner().clean(schema)


def test_combine_allof_fails_on_nested_conflicting_key() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "obj1": {
                        "properties": {
                            "key1": "value",
                        }
                    }
                },
            },
            {
                "properties": {
                    "obj1": {
                        "properties": {
                            "key1": "otherValue",
                        }
                    }
                },
            },
        ]
    }
    with pytest.raises(
        AssertionError,
        match=re.escape(
            "Error combining schemas, conflicting values for key 'key1': ['value', 'otherValue']"
        ),
    ):
        SchemaCleaner().clean(schema)


def test_combine_allof_with_ref() -> None:
    schema = {
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/nestedSchema"
            },
            {
                "properties": {"key2": "value"},
            },
        ],
        "$defs": {
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema": {
                "$id": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema",
                "$defs": {
                    "nestedSchema": {
                        "properties": {"nestedKey": "value"},
                        "required": ["nestedKey"],
                    },
                },
            }
        },
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {"nestedKey": "value", "key2": "value"},
            "required": [
                "nestedKey",
            ],
        },
    )


def test_combine_allof_required_only() -> None:
    schema = {
        "device document": {
            "items": {
                "allOf": [
                    {
                        "required": ["device type"],
                        "properties": {
                            "device type": {
                                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue"
                            },
                            "other value": {
                                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue"
                            },
                        },
                    },
                    {
                        "required": ["other value"],
                    },
                ]
            }
        }
    }

    validate_cleaned_schema(
        schema,
        {
            "device document": {
                "items": {
                    "properties": {
                        "device type": {
                            "$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/tStringValue"
                        },
                        "other value": {
                            "$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/tStringValue"
                        },
                    },
                    "required": [
                        "device type",
                        "other value",
                    ],
                }
            }
        },
    )


def test_combine_allof_with_nested_anyof() -> None:
    schema = {
        "allOf": [
            {"properties": {"key1": "value"}, "required": ["key1"]},
            {
                "anyOf": [
                    {"$ref": "#/$defs/schema1"},
                    {"$ref": "#/$defs/schema2"},
                ]
            },
        ],
        "$defs": {
            "schema1": {"properties": {"key2": "value"}},
            "schema2": {"properties": {"key3": "value"}},
        },
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {
                "key1": "value",
                "key2": "value",
                "key3": "value",
            },
            "required": ["key1"],
        },
    )


def test_combine_allof_with_nested_anyof_with_required_keys() -> None:
    schema = {
        "allOf": [
            {
                "properties": {"key1": "value"},
            },
            {
                "anyOf": [
                    {"$ref": "#/$defs/schema1"},
                    {"$ref": "#/$defs/schema2"},
                ]
            },
        ],
        "$defs": {
            "schema1": {"properties": {"key2": "value"}, "required": ["key2"]},
            "schema2": {"properties": {"key3": "value"}},
        },
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {
                    "properties": {
                        "key1": "value",
                        "key2": "value",
                        "key3": "value",
                    },
                    "required": ["key2"],
                },
                {
                    "properties": {
                        "key1": "value",
                        "key3": "value",
                    },
                },
            ]
        },
    )


def test_combine_allof_nested_oneof_and_anyof() -> None:
    schema = {
        "allOf": [
            {
                "properties": {"key1": "value"},
            },
            {
                "anyOf": [
                    {"properties": {"key2": "value"}, "required": ["key2"]},
                    {
                        "properties": {"key3": "value"},
                    },
                ]
            },
            {
                "oneOf": [
                    {
                        "properties": {"key4": "value"},
                    },
                    {
                        "properties": {"key5": "value"},
                    },
                ]
            },
        ],
    }
    validate_cleaned_schema(
        schema,
        {
            "oneOf": [
                {
                    "anyOf": [
                        {
                            "properties": {
                                "key1": "value",
                                "key2": "value",
                                "key3": "value",
                                "key4": "value",
                            },
                            "required": ["key2"],
                        },
                        {
                            "properties": {
                                "key1": "value",
                                "key3": "value",
                                "key4": "value",
                            },
                        },
                    ]
                },
                {
                    "anyOf": [
                        {
                            "properties": {
                                "key1": "value",
                                "key2": "value",
                                "key3": "value",
                                "key5": "value",
                            },
                            "required": ["key2"],
                        },
                        {
                            "properties": {
                                "key1": "value",
                                "key3": "value",
                                "key5": "value",
                            },
                        },
                    ]
                },
            ]
        },
    )


def test_combine_allof_items() -> None:
    schema = {
        "allOf": [
            {
                "items": {
                    "properties": {
                        "key1": "value",
                    },
                    "required": ["key1"],
                },
                "minItems": 1,
            },
            {
                "items": {
                    "properties": {
                        "key2": "value",
                    },
                },
                "minItems": 1,
            },
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "items": {
                "properties": {
                    "key1": "value",
                    "key2": "value",
                },
                "required": ["key1"],
            },
        },
    )


def test_combine_nested_allof() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "obj1": {
                        "allOf": [
                            {"properties": {"key1": "value"}, "required": ["key1"]},
                            {"properties": {"key2": "value"}},
                        ]
                    }
                },
            },
            {
                "properties": {
                    "obj1": {
                        "allOf": [
                            {"properties": {"key3": "value"}},
                            {"properties": {"key4": "value"}},
                        ]
                    }
                },
            },
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {
                "obj1": {
                    "properties": {
                        "key1": "value",
                        "key2": "value",
                        "key3": "value",
                        "key4": "value",
                    },
                    "required": ["key1"],
                }
            },
        },
    )


def test_combine_nested_oneof() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "obj1": {
                        "oneOf": [
                            {"properties": {"key1": "value"}, "required": ["key1"]},
                            {"properties": {"key2": "value"}},
                        ]
                    }
                },
            },
            {
                "properties": {
                    "obj1": {"properties": {"key3": "value"}},
                },
            },
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "properties": {
                "obj1": {
                    "oneOf": [
                        {
                            "properties": {"key1": "value", "key3": "value"},
                            "required": ["key1"],
                        },
                        {
                            "allOf": [
                                {"properties": {"key2": "value"}},
                                {"properties": {"key3": "value"}},
                            ]
                        },
                    ]
                }
            }
        },
    )


def test_deeply_nested_anyof_allof() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "obj": {
                        "allOf": [
                            {
                                "properties": {
                                    "sub": {"properties": {"key1": "value1a"}}
                                }
                            },
                            {"properties": {"other": "value"}},
                        ]
                    }
                }
            },
            {
                "anyOf": [
                    {
                        "properties": {
                            "obj": {
                                "properties": {
                                    "sub": {"properties": {"key2": "value2a"}}
                                }
                            }
                        }
                    },
                    {
                        "properties": {
                            "obj": {
                                "properties": {
                                    "sub": {"properties": {"key2": "value2b"}}
                                }
                            }
                        }
                    },
                ]
            },
        ]
    }
    validate_cleaned_schema(
        schema,
        {
            "anyOf": [
                {
                    "properties": {
                        "obj": {
                            "properties": {
                                "sub": {
                                    "allOf": [
                                        {"properties": {"key1": "value1a"}},
                                        {"properties": {"key2": "value2a"}},
                                    ]
                                },
                                "other": "value",
                            }
                        }
                    }
                },
                {
                    "properties": {
                        "obj": {
                            "properties": {
                                "sub": {
                                    "allOf": [
                                        {"properties": {"key1": "value1a"}},
                                        {"properties": {"key2": "value2b"}},
                                    ]
                                },
                                "other": "value",
                            }
                        }
                    }
                },
            ]
        },
    )


def test_anyof() -> None:
    import json

    with open("tests/allotrope/schema_parser/anyof_test_schema.json") as f:
        schema = json.load(f)

    cleaned = SchemaCleaner()._combine_anyof(schema)

    assert "anyOf" in json.dumps(cleaned)


def test_load_model() -> None:
    from allotropy.allotrope.models.adm.liquid_chromatography.rec._2023._09.liquid_chromatography import (
        Model,
    )

    Model(field_asm_manifest="fake_manifest")


def test_powerset_indices_from_index() -> None:
    assert _powerset_indices_from_index(0) == set()
    assert _powerset_indices_from_index(1) == {0}
    assert _powerset_indices_from_index(2) == {1}
    assert _powerset_indices_from_index(3) == {0, 1}
    assert _powerset_indices_from_index(63) == {0, 1, 2, 3, 4, 5}
    assert _powerset_indices_from_index(64) == {6}
