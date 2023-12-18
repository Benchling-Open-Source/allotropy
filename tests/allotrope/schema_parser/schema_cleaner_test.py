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


def test_blah():
    from allotropy.allotrope.models.liquid_chromatography_rec_2023_09_liquid_chromatography import (
        Model,
    )

    m = Model()
