from allotropy.allotrope.schema_parser.schema_cleaner import SchemaCleaner


def test_fixes_singlular_allof():
    schema = {
        "allOf": [
            {
                "key": "value"
            }
        ],
    }
    cleaned = SchemaCleaner().clean(schema)
    assert cleaned == {
        "key": "value"
    }


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
    assert SchemaCleaner().clean(schema) == expected

    # Flip so oneOf is first in allOf list, to cover all branches.
    schema["allOf"] = schema["allOf"][::-1]
    expected["oneOf"] = [
        {"allOf": value["allOf"][::-1]}
        for value in expected["oneOf"]
    ]
    assert SchemaCleaner().clean(schema) == expected


def test_clean_http_refs():
    schema = {
        "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/orderedItem"
    }
    assert SchemaCleaner().clean(schema) == {
        "$ref": "#/$defs/adm_core_REC_2023_09_core_schema/$defs/orderedItem"
    }

    schema = {
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/cube.schema#/$defs/tDatacube"
            },
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/cube.schema#/$defs/tDatacube"
            }
        ]
    }
    assert SchemaCleaner().clean(schema) == {
        "allOf": [
            {
                "$ref": "#/$defs/adm_core_REC_2023_09_cube_schema/$defs/tDatacube"
            },
            {
                "$ref": "#/$defs/adm_core_REC_2023_09_cube_schema/$defs/tDatacube"
            }
        ]
    }


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
        ]
    }

    assert SchemaCleaner().clean(schema) == {
        "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001233",
        "$asm.pattern": "quantity datum",
        "$ref": "#/$defs/tQuantityValueUnitless"
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
                    "$ref": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema#/$defs/mV.s"
                }
            ]
        },
        "$defs": {
            "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema": {
                "$id": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema",
                "$comment": "Auto-generated from QUDT 1.1 and Allotrope Extensions for QUDT",
                "$defs": {
                    "mV.s": {
                        "properties": {
                            "unit": {
                                "type": "string",
                                "const": "mV.s",
                                "$asm.unit-iri": "http://purl.allotrope.org/ontology/qudt-ext/unit#MillivoltTimesSecond"
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

    assert SchemaCleaner().clean(schema) == {
        "properties": {
            "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001233",
            "$asm.pattern": "quantity datum",
            "$ref": "#/$defs/tQuantityValueMillivoltTimesSecond"

        },
        "$defs": {}
    }


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

    assert SchemaCleaner().clean(schema) == {
        "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001180",
        "$asm.pattern": "quantity datum",
        "oneOf": [
            {
                "$ref": "#/$defs/tQuantityValueMilliSecond"
            },
            {
                "$ref": "#/$defs/tQuantityValuePercent"
            }
        ]
    }


def test_replace_definiton() -> None:
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
                    "tQuantityValue": {
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
                }
            }
        }
    }
    assert SchemaCleaner.clean(schema) == {
        "properties": {
            "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0001180",
            "$asm.pattern": "quantity datum",
            "$ref": "#/$defs/tQuantityValue"
        },
        "$defs": {
            "adm_core_REC_2023_09_core_schema": {
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
                                        "$ref": "#/$defs/adm_core_REC_2023_09_manifest_schema"
                                    }
                                ]
                            }
                        }
                    },
                }
            }
        }
    }
