import re
from typing import Any, Optional

from deepdiff import DeepDiff
import pytest

from allotropy.allotrope.schema_parser.schema_cleaner import SchemaCleaner


def validate_cleaned_schema(schema: dict[str, Any], expected: dict[str, Any], *, test_defs: Optional[bool] = False):
    # Add $defs/<core schema>/$defs/tQuantityValue as it is used for many tests.
    if "$defs" not in schema:
        schema["$defs"] = {}
    if "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema" not in schema["$defs"]:
        schema["$defs"]["http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema"] = {"$defs": {}}
    schema["$defs"]["http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema"]["$defs"]["tQuantityValue"] = {
        "type": "object",
        "properties": {
            "value": {
                "type": "number"
            },
            "unit": {
                "$ref": "#/$defs/tUnit"
            },
            "has statistic datum role": {
                "$ref": "#/$defs/tStatisticDatumRole"
            },
            "@type": {
                "$ref": "#/$defs/tClass"
            }
        },
        "$asm.type": "http://qudt.org/schema/qudt#QuantityValue",
        "required": [
            "value",
            "unit"
        ]
    }
    actual = SchemaCleaner().clean(schema)

    if not test_defs:
        actual.pop("$defs", None)
        expected.pop("$defs", None)

    import json
    print("^^^^")
    print(json.dumps(actual, indent=4))
    # print(DeepDiff(expected, actual, exclude_regex_paths=exclude_regex))
    assert not DeepDiff(
        expected,
        actual,
    )


def test_clean_http_refs():
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
        "$defs": defs_schema
    }
    validate_cleaned_schema(schema, {
        "$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/orderedItem"
    })

    schema = {
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/orderedItem"
            },
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tNumberArray"
            }
        ],
        "$defs": defs_schema
    }
    validate_cleaned_schema(schema, {
        "allOf": [
            {
                "$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/orderedItem"
            },
            {
                "$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/tNumberArray"
            }
        ]
    })


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
            }
        ],
    }
    validate_cleaned_schema(schema, {
        "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001233",
        "$asm.pattern": "quantity datum",
        "$ref": "#/$defs/tQuantityValueUnitless",
    })


def test_add_missing_unit() -> None:
    schema = {
        "properties": {
            "$ref": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema#/$defs/fake-unit"
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
                                "$asm.unit-iri": "http://purl.allotrope.org/ontology/qudt-ext/unit#FakeUnit"
                            }
                        },
                        "required": [
                            "unit"
                        ]
                    }
                }
            }
        }
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "$ref": "#/$defs/FakeUnit"
        },
    })


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
                }
            ]
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
                                "$asm.unit-iri": "http://purl.allotrope.org/ontology/qudt-ext/unit#FakeUnit"
                            }
                        },
                        "required": [
                            "unit"
                        ]
                    }
                }
            },
        }
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001233",
            "$asm.pattern": "quantity datum",
            "$ref": "#/$defs/tQuantityValueFakeUnit"
        }
    })


def test_fix_quantity_value_reference_after_oneof_nested_in_allof():
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
                    }
                ]
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001180",
        "$asm.pattern": "quantity datum",
        "oneOf": [
            {
                "$ref": "#/$defs/tQuantityValueMilliSecond"
            },
            {
                "$ref": "#/$defs/tQuantityValuePercent"
            }
        ],
    })


def test_replace_definiton() -> None:
    # tQuantityValue in core.schema matches the schema of tQuantityValue in shared/definitions.json, so the
    # ref will be replaced by that, and tQuantityValue will be removed from cleaned defs.
    # asm is not in shared/definitions, so it will be preserved.
    schema = {
        "properties": {
            "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001180",
            "$asm.pattern": "quantity datum",
            "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tQuantityValue"
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
                                    {
                                        "type": "string",
                                        "format": "iri"
                                    },
                                    {
                                        "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/manifest.schema"
                                    }
                                ]
                            }
                        }
                    },
                }
            }
        }
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001180",
            "$asm.pattern": "quantity datum",
            "$ref": "#/$defs/tQuantityValue"
        },
        "$defs": {
            "adm_core_REC_2023_09_core_schema": {
                "$defs": {
                    "asm": {
                        "properties": {
                            "$asm.manifest": {
                                "oneOf": [
                                    {
                                        "type": "string",
                                        "format": "iri"
                                    },
                                    {
                                        "$ref": "#/$defs/adm_core_REC_2023_09_manifest_schema"
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    }, test_defs=True)


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
                                {
                                    "$ref": "#/$defs/nestedSchema"
                                },
                                {
                                    "$ref": "#/$defs/otherSchema"
                                },
                                {
                                    "$ref": "#/$defs/tQuantityValue"
                                }
                            ]
                        }
                    },
                    "nestedSchema": {
                        "properties": {
                            "type": "string"
                        }
                    },
                }
            },
            "otherSchema": {
                "properties": {
                    "key": "string",
                }
            },
        }
    }
    validate_cleaned_schema(schema, {
        "$defs": {
            "adm_core_REC_2023_09_hierarchy_schema": {
                "$defs": {
                    "anotherThing": {
                        "properties": {
                            "allOf": [
                                {
                                    "$ref": "#/$defs/tQuantityValue"
                                },
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
                                {
                                    "$ref": "#/$defs/otherSchema"
                                },
                                {
                                    "$ref": "#/$defs/tQuantityValue"
                                }
                            ]
                        }
                    },
                    "nestedSchema": {
                        "properties": {
                            "type": "string"
                        }
                    }
                }
            },
            "otherSchema": {
                "properties": {
                    "key": "string",
                }
            },
        }
    }, test_defs=True)


def test_singular_anyof():
    schema = {
        "anyOf": [
            {
                "items": {
                    "properties": {
                        "key1": "value"
                    }
                },
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "items": {
            "properties": {
                "key1": "value",
            }
        },
    })


def test_combine_anyof_non_conflicting_optional_keys():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": "value",
                }
            },
            {
                "properties": {
                    "key2": "value"
                }
            },
            {
                "properties": {
                    "key3": "value"
                }
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "key1": "value",
            "key2": "value",
            "key3": "value"
        }
    })


def test_combine_anyof_with_conflicting_keys():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": "value",
                    "key2": "value"
                }
            },
            {
                "properties": {
                    "key1": "otherValue",
                    "key3": "value"
                }
            },
            {
                "properties": {
                    "key4": "value"
                }
            },
        ]
    }
    validate_cleaned_schema(schema, {
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
    })


def test_combine_anyof_with_multiple_conflicting_keys():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": "value",
                    "key2": "value"
                }
            },
            {
                "properties": {
                    "key1": "otherValue",
                    "key2": "otherValue"
                }
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "key1": "otherValue",
                    "key2": "otherValue"
                }
            },
            {
                "properties": {
                    "key1": "value",
                    "key2": "value"
                }
            },
        ]
    })


def test_combine_anyof_with_nested_conflicting_keys() -> None:
    schema = {
        "anyOf": [
            {
                "properties": {
                    "obj1": {
                        "properties": {
                            "key1": "string"
                        }
                    },
                    "field1": "value"
                }
            },
            {
                "properties": {
                    "obj1": {
                        "properties": {
                            "key1": "boolean"
                        }
                    },
                }
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "obj1": {
                        "properties": {
                            "key1": "boolean"
                        }
                    },
                }
            },
            {
                "properties": {
                    "obj1": {
                        "properties": {
                            "key1": "string"
                        }
                    },
                    "field1": "value"
                }
            },
        ]
    })


def test_combine_anyof_with_nested_anyof() -> None:
    schema = {
        "anyOf": [
            {
                "properties": {
                    "obj1": {
                        "anyOf": [
                            {
                                "properties": {
                                    "key1": "value"
                                }
                            },
                            {
                                "properties": {
                                    "key2": "value"
                                }
                            }
                        ]
                    }
                }
            },
            {
                "properties": {
                    "obj1": {
                        "anyOf": [
                            {
                                "properties": {
                                    "key3": "value"
                                }
                            },
                            {
                                "properties": {
                                    "key4": "value"
                                }
                            }
                        ]
                    }
                }
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "obj1": {
                "allOf": [
                    {
                        "properties": {
                            "key1": "value",
                            "key2": "value"
                        }
                    },
                    {
                        "properties": {
                            "key3": "value",
                            "key4": "value"
                        }
                    }
                ]
            }
        }
    })


def test_combine_anyof_with_required_values():
    schema = {
        "anyOf": [
            {
                "items": {
                    "properties": {
                        "key1": "value"
                    },
                    "required": ["key1"]
                },
                "minItems": 0
            },
            {
                "items": {
                    "properties": {
                        "key2": "value"
                    }
                },
                "minItems": 0
            },
            {
                "items": {
                    "properties": {
                        "key3": "value"
                    }
                },
                "minItems": 0
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "items": {
                    "properties": {
                        "key1": "value",
                        "key2": "value",
                        "key3": "value"
                    },
                    "required": ["key1"]
                },
            },
            {
                "items": {
                    "properties": {
                        "key2": "value",
                        "key3": "value"
                    }
                },
            },
        ]
    })


def test_combine_anyof_with_multiple_required_values():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": "value",
                    "key2": "value"
                },
                "required": ["key1", "key2"]
            },
            {
                "properties": {
                    "key3": "value"
                }
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "key1": "value",
                    "key2": "value",
                    "key3": "value"
                },
                "required": ["key1", "key2"]
            },
            {
                "properties": {
                    "key3": "value"
                }
            },
        ]
    })


def test_combine_anyof_with_multiple_required_value_sets():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": "value",
                    "key2": "value",
                    "key3": "value"
                },
                "required": ["key1", "key2"]
            },
            {
                "properties": {
                    "key2": "value",
                    "key3": "value"
                }
            },
            {
                "properties": {
                    "key4": "value"
                },
                "required": ["key4"]
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "key1": "value",
                    "key2": "value",
                    "key3": "value",
                    "key4": "value"
                },
                "required": ["key1", "key2", "key4"]
            },
            {
                "properties": {
                    "key2": "value",
                    "key3": "value",
                    "key4": "value"
                },
                "required": ["key4"]
            },
            {
                "properties": {
                    "key1": "value",
                    "key2": "value",
                    "key3": "value"
                },
                "required": ["key1", "key2"]
            },
            {
                "properties": {
                    "key2": "value",
                    "key3": "value"
                }
            },
        ]
    })


def test_combine_anyof_with_parent_object():
    schema = {
        "items": {
            "properties": {
                "parentKey": "value"
            },
            "anyOf": [
                {
                    "properties": {
                        "key1": "value"
                    }
                },
                {
                    "properties": {
                        "key2": "value"
                    }
                },
            ]
        },
        "minItems": 1
    }
    validate_cleaned_schema(schema, {
        "items": {
            "allOf": [
                {
                    "properties": {
                        "parentKey": "value"
                    }
                },
                {
                    "properties": {
                        "key1": "value",
                        "key2": "value"
                    }
                }
            ]
        }
    })


def test_combine_anyof_with_parent_object_with_required_keys():
    schema = {
        "properties": {
            "parentKey": "value",
        },
        "required": ["parentKey"],
        "anyOf": [
            {
                "properties": {
                    "childKey": "value"
                },
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "parentKey": "value",
            "childKey": "value"
        },
        "required": ["parentKey"]
    })


def test_combine_anyof_with_parent_object_with_child_required_keys():
    schema = {
        "properties": {
            "parentKey": "value",
        },
        "required": ["parentKey"],
        "anyOf": [
            {
                "properties": {
                    "childKey1": "value"
                },
            },
            {
                "properties": {
                    "childKey2": "value"
                },
                "required": ["childKey2"],
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "parentKey": "value",
                    "childKey1": "value",
                    "childKey2": "value"
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
    })


def test_combine_anyof_with_parent_anyof_required_keys():
    schema = {
        "properties": {
            "key1": "value",
            "key2": "otherValue",
        },
        "anyOf": [
            {
                "required": ["key1"]
            },
            {
                "required": ["key2"]
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "key1": "value",
                    "key2": "otherValue"
                },
                "required": [
                    "key1",
                    "key2"
                ]
            },
            {
                "properties": {
                    "key1": "value",
                    "key2": "otherValue"
                },
                "required": [
                    "key1"
                ]
            },
            {
                "properties": {
                    "key1": "value",
                    "key2": "otherValue"
                },
                "required": [
                    "key2"
                ]
            }
        ]
    })


def test_fixes_singlular_allof():
    schema = {
        "allOf": [
            {
                "key": "value"
            }
        ],
    }
    validate_cleaned_schema(schema, {
        "key": "value"
    })


def test_fixes_oneof_nested_in_allof():
    schema = {
        "allOf": [
            {
                "properties": {
                    "key1": "value1"
                }
            },
            {
                "oneOf": [
                    {
                        "properties": {
                            "key2": "value2"
                        }
                    },
                    {
                        "properties": {
                            "key3": "value3"
                        }
                    }
                ]
            }
        ]
    }
    expected = {
        "oneOf": [
            {
                "allOf": [
                    {
                        "properties": {
                            "key1": "value1"
                        }
                    },
                    {
                        "properties": {
                            "key2": "value2"
                        }
                    }
                ]
            },
            {
                "allOf": [
                    {
                        "properties": {
                            "key1": "value1"
                        }
                    },
                    {
                        "properties": {
                            "key3": "value3"
                        }
                    }
                ]
            }
        ]
    }
    validate_cleaned_schema(schema, expected)

    # Flip so oneOf is first in allOf list, to cover all branches.
    schema["allOf"] = schema["allOf"][::-1]
    expected["oneOf"] = [
        {"allOf": value["allOf"][::-1]}
        for value in expected["oneOf"]
    ]
    validate_cleaned_schema(schema, expected)


def test_fixes_oneof_nested_in_allof_in_reference():
    schema = {
        "allOf": [
            {
                "properties": {
                    "key1": "value1"
                }
            },
            {
                "$ref": "#/$defs/oneOfSchema"
            }
        ],
        "$defs": {
            "oneOfSchema": {
                "oneOf": [
                    {
                        "properties": {
                            "key2": "value2"
                        }
                    },
                    {
                        "properties": {
                            "key3": "value3"
                        }
                    }
                ]
            }
        }
    }
    expected = {
        "oneOf": [
            {
                "allOf": [
                    {
                        "properties": {
                            "key1": "value1"
                        }
                    },
                    {
                        "properties": {
                            "key2": "value2"
                        }
                    }
                ]
            },
            {
                "allOf": [
                    {
                        "properties": {
                            "key1": "value1"
                        }
                    },
                    {
                        "properties": {
                            "key3": "value3"
                        }
                    }
                ]
            }
        ]
    }
    validate_cleaned_schema(schema, expected)


def test_combine_allof():
    schema = {
        "allOf": [
            {
                "properties": {
                    "key1": "value"
                },
                "required": ["key1"]
            },
            {
                "properties": {
                    "key2": "value"
                }
            },
            {
                "properties": {
                    "key3": "otherValue"
                }
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "key1": "value",
            "key2": "value",
            "key3": "otherValue"
        },
        "required": ["key1"]
    })


def test_combine_allof_key_with_matching_value():
    schema = {
        "allOf": [
            {
                "properties": {
                    "key1": "value"
                },
                "required": ["key1"]
            },
            {
                "properties": {
                    "key1": "value",
                    "key2": "value"
                }
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "key1": "value",
            "key2": "value",
        },
        "required": ["key1"]
    })


def test_combine_allof_fails_on_conflicting_key():
    schema = {
        "allOf": [
            {
                "properties": {
                    "key1": "value"
                },
                "required": ["key1"]
            },
            {
                "properties": {
                    "key1": "otherValue"
                }
            },
        ]
    }
    with pytest.raises(AssertionError, match=re.escape("Error combining schemas, conflicting values for key 'key1': ['value', 'otherValue']")):
        SchemaCleaner().clean(schema)


def test_combine_allof_fails_on_nested_conflicting_key():
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
    with pytest.raises(AssertionError, match=re.escape("Error combining schemas, conflicting values for key 'key1': ['value', 'otherValue']")):
        SchemaCleaner().clean(schema)


def test_combine_allof_with_ref():
    schema = {
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/nestedSchema"
            },
            {
                "properties": {
                    "key2": "value"
                },
            },
        ],
        "$defs": {
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema": {
                "$id": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema",
                "$defs": {
                    "nestedSchema": {
                        "properties": {
                            "nestedKey": "value"
                        },
                        "required": ["nestedKey"]
                    },
                }
            }
        }
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "nestedKey": "value",
            "key2": "value"
        },
        "required": [
            "nestedKey",
        ]
    })


def test_combine_allof_required_only() -> None:
    schema = {
        "device document": {
            "items": {
                "allOf": [
                    {
                        "required": [
                            "device type"
                        ],
                        "properties": {
                            "device type": {
                                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue"
                            },
                            "other value": {
                                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue"
                            },
                        }
                    },
                    {
                        "required": [
                            "other value"
                        ],
                    },
                ]
            }
        }
    }

    validate_cleaned_schema(schema, {
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
    })


def test_combine_allof_with_nested_anyof() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "key1": "value"
                },
                "required": ["key1"]
            },
            {
                "anyOf": [
                    {
                        "$ref": "#/$defs/schema1"
                    },
                    {
                        "$ref": "#/$defs/schema2"
                    },
                ]
            },
        ],
        "$defs": {
            "schema1": {
                "properties": {
                    "key2": "value"
                }
            },
            "schema2": {
                "properties": {
                    "key3": "value"
                }
            }
        }
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "key1": "value",
            "key2": "value",
            "key3": "value",
        },
        "required": ["key1"]
    })


def test_combine_allof_with_nested_anyof_with_required_keys() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "key1": "value"
                },
            },
            {
                "anyOf": [
                    {
                        "$ref": "#/$defs/schema1"
                    },
                    {
                        "$ref": "#/$defs/schema2"
                    },
                ]
            },
        ],
        "$defs": {
            "schema1": {
                "properties": {
                    "key2": "value"
                },
                "required": ["key2"]
            },
            "schema2": {
                "properties": {
                    "key3": "value"
                }
            }
        }
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "key1": "value",
                    "key2": "value",
                    "key3": "value",
                },
                "required": ["key2"]
            },
            {
                "properties": {
                    "key1": "value",
                    "key3": "value",
                },
            },
        ]
    })


def test_combine_allof_nested_oneof_and_anyof() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "key1": "value"
                },
            },
            {
                "anyOf": [
                    {
                        "properties": {
                            "key2": "value"
                        },
                        "required": ["key2"]
                    },
                    {
                        "properties": {
                            "key3": "value"
                        },
                    },
                ]
            },
            {
                "oneOf": [
                    {
                        "properties": {
                            "key4": "value"
                        },
                    },
                    {
                        "properties": {
                            "key5": "value"
                        },
                    },
                ]
            },
        ],
    }
    validate_cleaned_schema(schema, {
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
                        "required": ["key2"]
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
                        "required": ["key2"]
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
    })


def test_combine_allof_items() -> None:
    schema = {
        "allOf": [
            {
                "items": {
                    "properties": {
                        "key1": "value",
                    },
                    "required": ["key1"]
                },
                "minItems": 1
            },
            {
                "items": {
                    "properties": {
                        "key2": "value",
                    },
                },
                "minItems": 1
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "items": {
            "properties": {
                "key1": "value",
                "key2": "value",
            },
            "required": ["key1"]
        },
    })


def test_combine_nested_allof() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "obj1": {
                        "allOf": [
                            {
                                "properties": {
                                    "key1": "value"
                                },
                                "required": ["key1"]
                            },
                            {
                                "properties": {
                                    "key2": "value"
                                }
                            }
                        ]
                    }
                },
            },
            {
                "properties": {
                    "obj1": {
                        "allOf": [
                            {
                                "properties": {
                                    "key3": "value"
                                }
                            },
                            {
                                "properties": {
                                    "key4": "value"
                                }
                            }
                        ]
                    }
                },
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "obj1": {
                "properties": {
                    "key1": "value",
                    "key2": "value",
                    "key3": "value",
                    "key4": "value",
                },
                "required": ["key1"]
            }
        },
    })


def test_combine_nested_oneof() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "obj1": {
                        "oneOf": [
                            {
                                "properties": {
                                    "key1": "value"
                                },
                                "required": ["key1"]
                            },
                            {
                                "properties": {
                                    "key2": "value"
                                }
                            }
                        ]
                    }
                },
            },
            {
                "properties": {
                    "obj1": {
                        "properties": {
                            "key3": "value"
                        }
                    },
                },
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "obj1": {
                "oneOf": [
                    {
                        "properties": {
                            "key1": "value",
                            "key3": "value"
                        },
                        "required": [
                            "key1"
                        ]
                    },
                    {
                        "allOf": [
                            {
                                "properties": {
                                    "key2": "value"
                                }
                            },
                            {
                                "properties": {
                                    "key3": "value"
                                }
                            }
                        ]
                    }
                ]
            }
        }
    })


def test_deeply_nested_anyof_allof() -> None:
    schema = {
        "allOf": [
            {
                "properties": {
                    "obj": {
                        "allOf": [
                            {
                                "properties": {
                                    "sub": {
                                        "properties": {
                                            "key1": "value1a"
                                        }
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "other": "value"
                                }
                            }
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
                                    "sub": {
                                        "properties": {
                                            "key2": "value2a"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    {
                        "properties": {
                            "obj": {
                                "properties": {
                                    "sub": {
                                        "properties": {
                                            "key2": "value2b"
                                        }
                                    }
                                }
                            }
                        }
                    }
                ]
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "obj": {
                        "properties": {
                            "sub": {
                                "allOf": [
                                    {
                                        "properties": {
                                            "key1": "value1a"
                                        }
                                    },
                                    {
                                        "properties": {
                                            "key2": "value2a"
                                        }
                                    }
                                ]
                            },
                            "other": "value"
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
                                    {
                                        "properties": {
                                            "key1": "value1a"
                                        }
                                    },
                                    {
                                        "properties": {
                                            "key2": "value2b"
                                        }
                                    }
                                ]
                            },
                            "other": "value"
                        }
                    }
                }
            }
        ]
    })


# @pytest.mark.skip()
def test_missing_values() -> None:
    import json
    with open("tests/allotrope/schema_parser/test_schema.json") as f:
        schema = json.load(f)

    cleaned = SchemaCleaner().clean(schema)

    with open("tests/allotrope/schema_parser/output_schema.json", "w") as f:
        json.dump(cleaned, f)

    assert "detector offset setting" in json.dumps(cleaned)
    # assert "anyOf" in json.dumps(cleaned)


@pytest.mark.skip()
def test_load_model() -> None:
    from allotropy.allotrope.models.liquid_chromatography_rec_2023_09_liquid_chromatography import (
        Model,
    )

    model = Model()


#@pytest.mark.skip()
def test_anyof() -> None:
    import json
    with open("tests/allotrope/schema_parser/anyof_test_schema.json") as f:
        schema = json.load(f)

    cleaned = SchemaCleaner()._combine_anyof(schema)

    with open("tests/allotrope/schema_parser/anyof_output_schema.json", "w") as f:
        json.dump(cleaned, f)

    assert "anyOf" in json.dumps(cleaned)
