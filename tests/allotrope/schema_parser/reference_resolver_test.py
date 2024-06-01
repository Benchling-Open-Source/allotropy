import os
from unittest import mock

from allotropy.allotrope.schema_parser.path_util import SCHEMA_DIR_PATH
from allotropy.allotrope.schema_parser.reference_resolver import (
    _download_schema,
    _get_schema_from_reference,
    get_references,
    resolve_references,
    schema_path_from_reference,
)


def test_get_schema_from_reference() -> None:
    assert (
        _get_schema_from_reference(
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue"
        )
        == "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema"
    )
    assert (
        _get_schema_from_reference(
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/hierarchy.schema#/$defs/techniqueAggregateDocument"
        )
        == "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/hierarchy.schema"
    )
    assert (
        _get_schema_from_reference(
            "core/BENCHLING/2023/09/hierarchy.schema#/$defs/techniqueAggregateDocument"
        )
        == "core/BENCHLING/2023/09/hierarchy.schema"
    )


def test_get_references() -> None:
    schema = {
        "properties": {
            "pump model number": {
                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002530",
                "$asm.pattern": "value datum",
                "$asm.type": "http://www.w3.org/2001/XMLSchema#string",
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue",
            },
            "detector model number": {
                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002489",
                "$asm.pattern": "value datum",
                "$asm.type": "http://www.w3.org/2001/XMLSchema#string",
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue",
            },
        }
    }
    references = get_references(schema)

    assert references == {
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema"
    }


def test_get_references_allof() -> None:
    schema = {
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/hierarchy.schema#/$defs/techniqueAggregateDocument"
            },
            {
                "type": "object",
                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002524",
                "$asm.pattern": "aggregate datum",
                "properties": {
                    "device system document": {
                        "properties": {
                            "pump model number": {
                                "$asm.property-class": "http://purl.allotrope.org/ontologies/result#AFR_0002530",
                                "$asm.pattern": "value datum",
                                "$asm.type": "http://www.w3.org/2001/XMLSchema#string",
                                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tStringValue",
                            },
                        }
                    }
                },
            },
        ]
    }
    references = get_references(schema)

    assert references == {
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema",
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/hierarchy.schema",
    }


def test_get_references_oneof_allof() -> None:
    schema = {
        "allOf": [
            {
                "$ref": "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema#/$defs/tQuantityValue"
            },
            {
                "oneOf": [
                    {
                        "$ref": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema#/$defs/s"
                    },
                    {
                        "$ref": "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema#/$defs/mL"
                    },
                ]
            },
        ]
    }
    references = get_references(schema)

    assert references == {
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema",
        "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema",
    }


def test_schema_path_from_reference() -> None:
    assert (
        schema_path_from_reference(
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema"
        )
        == "adm/core/REC/2023/09/core.schema"
    )
    assert (
        schema_path_from_reference(
            "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema"
        )
        == "qudt/REC/2023/09/units.schema"
    )


def test_resolve_references() -> None:
    references = {
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/fake.schema",
    }
    with mock.patch(
        "allotropy.allotrope.schema_parser.reference_resolver._download_schema"
    ) as mock_download:
        schema_paths = resolve_references(references)
        assert schema_paths == {"adm/core/REC/2023/09/fake.schema"}
        mock_download.assert_called_once_with(
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/fake.schema",
            "adm/core/REC/2023/09/fake.schema",
        )


def test_download_schema() -> None:
    with mock.patch(
        "allotropy.allotrope.schema_parser.reference_resolver.urllib.request.urlretrieve"
    ) as mock_urlretrieve:
        _download_schema(
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema",
            "adm/core/REC/2023/09/core.schema",
        )
        mock_urlretrieve.assert_called_once_with(
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema",
            os.path.join(SCHEMA_DIR_PATH, "adm/core/REC/2023/09/core.schema.json"),
        )
