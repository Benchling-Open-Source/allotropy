from allotropy.allotrope.schema_parser.schema_cleaner import SchemaCleaner


def test_schema_cleaner_singlular_allof():
    schema = {
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tQuantityValue"
            }
        ],
    }
    schema_cleaner = SchemaCleaner(schema)
    cleaned = schema_cleaner.clean()
    assert cleaned == {
        "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tQuantityValue"
    }
