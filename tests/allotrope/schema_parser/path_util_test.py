from allotropy.allotrope.schema_parser.path_util import get_schema_path_from_reference


def test_get_schema_path_from_reference() -> None:
    assert (
        get_schema_path_from_reference(
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema"
        )
        == "adm/core/REC/2023/09/core.schema.json"
    )
    assert (
        get_schema_path_from_reference(
            "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema"
        )
        == "qudt/REC/2023/09/units.schema.json"
    )
