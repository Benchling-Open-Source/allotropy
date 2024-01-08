from typing import Any, Optional

from deepdiff import DeepDiff

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
                "key1": "value1"
            },
            {
                "oneOf": [
                    {
                        "key2": "value2"
                    },
                    {
                        "key3": "value3"
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
                        "key1": "value1"
                    },
                    {
                        "key2": "value2"
                    },
                ]
            },
            {
                "allOf": [
                    {
                        "key1": "value1"
                    },
                    {
                        "key3": "value3"
                    },
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


def test_clean_http_refs():
    schema = {
        "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/orderedItem"
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
        ]
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
            }
        }
    }, test_defs=True)


def test_singular_anyof():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    }
                }
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "key1": {
                "type": "string"
            },
        }
    })


def test_combine_anyof_non_conflicting_optional_keys():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "key2": {
                        "type": "string"
                    }
                }
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "key1": {
                "type": "string"
            },
            "key2": {
                "type": "string"
            }
        }
    })


def test_combine_anyof_with_conflicting_keys():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "key2": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "key1": {
                        "type": "boolean"
                    }
                }
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    },
                    "key2": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "key1": {
                        "type": "boolean"
                    },
                    "key2": {
                        "type": "string"
                    }
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
                    "field1": {
                        "type": "string"
                    }
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
                            "key1": "string"
                        }
                    },
                    "field1": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "obj1": {
                        "properties": {
                            "key1": "boolean"
                        }
                    },
                    "field1": {
                        "type": "string"
                    }
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
                                    "key1": {
                                        "type": "string"
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "key2": {
                                        "type": "string"
                                    }
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
                                    "key3": {
                                        "type": "string"
                                    }
                                }
                            },
                            {
                                "properties": {
                                    "key4": {
                                        "type": "string"
                                    }
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
                "properties": {
                    "key1": {
                        "type": "string"
                    },
                    "key2": {
                        "type": "string"
                    },
                    "key3": {
                        "type": "string"
                    },
                    "key4": {
                        "type": "string"
                    }
                }
            },
        }
    })


def test_combine_anyof_with_required_values():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    }
                },
                "required": ["key1"]
            },
            {
                "properties": {
                    "key2": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "key3": {
                        "type": "string"
                    }
                }
            }
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "key2": {
                        "type": "string"
                    },
                    "key3": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    },
                    "key2": {
                        "type": "string"
                    },
                    "key3": {
                        "type": "string"
                    }
                },
                "required": ["key1"]
            }
        ]
    })


def test_combine_anyof_with_multiple_required_values():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    },
                    "key2": {
                        "type": "string"
                    }
                },
                "required": ["key1", "key2"]
            },
            {
                "properties": {
                    "key3": {
                        "type": "string"
                    }
                }
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "key3": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    },
                    "key2": {
                        "type": "string"
                    },
                    "key3": {
                        "type": "string"
                    }
                },
                "required": ["key1", "key2"]
            }
        ]
    })


def test_combine_anyof_with_multiple_required_value_sets():
    schema = {
        "anyOf": [
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    },
                    "key2": {
                        "type": "string"
                    },
                    "key3": {
                        "type": "string"
                    }
                },
                "required": ["key1", "key2"]
            },
            {
                "properties": {
                    "key2": {
                        "type": "string"
                    },
                    "key3": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "key4": {
                        "type": "string"
                    }
                },
                "required": ["key4"]
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "anyOf": [
            {
                "properties": {
                    "key3": {
                        "type": "string"
                    }
                }
            },
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    },
                    "key2": {
                        "type": "string"
                    },
                    "key3": {
                        "type": "string"
                    }
                },
                "required": ["key1", "key2"]
            },
            {
                "properties": {
                    "key3": {
                        "type": "string"
                    },
                    "key4": {
                        "type": "string"
                    }
                },
                "required": ["key4"]
            },
            {
                "properties": {
                    "key1": {
                        "type": "string"
                    },
                    "key2": {
                        "type": "string"
                    },
                    "key3": {
                        "type": "string"
                    },
                    "key4": {
                        "type": "string"
                    }
                },
                "required": ["key1", "key2", "key4"]
            },
        ]
    })


def test_combine_anyof_with_parent_object():
    schema = {
        "properties": {
            "parentKey": {
                "type": "string",
            }
        },
        "anyOf": [
            {
                "properties": {
                    "childKey": {
                        "type": "string"
                    }
                }
            },
        ]
    }
    validate_cleaned_schema(schema, {
        "properties": {
            "parentKey": {
                "type": "string"
            },
            "childKey": {
                "type": "string"
            }
        }
    })


"""
def test_fix_allof_optional_before_required() -> None:
    schema = {
        "device document": {
            "type": "array",
            "$asm.pattern": "indexed datum",
            "items": {
                "allOf": [
                    {
                        "type": "object",
                        "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002567",
                        "$asm.pattern": "aggregate datum",
                        "required": [
                            "device type"
                        ],
                        "properties": {
                            "device type": {
                                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002568",
                                "$asm.pattern": "value datum",
                                "$asm.type": "http://www.w3.org/2001/XMLSchema#string",
                                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue"
                            },
                            "other value": {
                                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002568",
                                "$asm.pattern": "value datum",
                                "$asm.type": "http://www.w3.org/2001/XMLSchema#string",
                                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue"
                            },
                        }
                    },
                    {
                        "required": [
                            "other value"
                        ],
                    },
                    {
                        "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/orderedItem"
                    }
                ]
            }
        },
        "$defs": {
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema": {
                "$defs": {
                    "orderedItem": {
                        "properties": {
                            "@index": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 2147483647
                            }
                        }
                    }
                }
            }
        }
    }

    import json
    print(json.dumps(SchemaCleaner().clean(schema), indent=4))

    assert SchemaCleaner().clean(schema) == {
        "device document": {
            "type": "array",
            "$asm.pattern": "indexed datum",
            "items": {
                "type": "object",
                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002567",
                "$asm.pattern": "aggregate datum",
                "required": ["other value", "device type"],
                "properties": {
                    "device type": {
                        "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002568",
                        "$asm.pattern": "value datum",
                        "$asm.type": "http://www.w3.org/2001/XMLSchema#string",
                        "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue"
                    },
                    "other value": {
                        "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002568",
                        "$asm.pattern": "value datum",
                        "$asm.type": "http://www.w3.org/2001/XMLSchema#string",
                        "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue"
                    },
                    "@index": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 2147483647
                    }
                }
            }
        },
        "$defs": {
            "adm_core_REC_2023_09_core_schema": {
                "$defs": {
                    "orderedItem": {
                        "properties": {
                            "@index": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 2147483647
                            }
                        }
                    }
                }
            }
        }
    }
"""

def test_load_model() -> None:
    from allotropy.allotrope.models.liquid_chromatography_rec_2023_09_liquid_chromatography import (
        Model,
    )

    model = Model()
