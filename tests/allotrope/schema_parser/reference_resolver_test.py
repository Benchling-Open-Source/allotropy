from pathlib import Path
from unittest import mock

from allotropy.allotrope.schema_parser.path_util import SCHEMA_DIR_PATH
from allotropy.allotrope.schema_parser.reference_resolver import (
    _download_references,
    _get_references,
    _get_schema_from_reference,
    download_schema,
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
            "adm/core/BENCHLING/2023/09/hierarchy.schema#/$defs/techniqueAggregateDocument"
        )
        == "adm/core/BENCHLING/2023/09/hierarchy.schema"
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
    references = _get_references(schema)

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
    references = _get_references(schema)

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
    references = _get_references(schema)

    assert references == {
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/core.schema",
        "http://purl.allotrope.org/json-schemas/qudt/REC/2023/09/units.schema",
    }


def test_resolve_references() -> None:
    references = {
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/fake.schema",
    }
    with mock.patch(
        "allotropy.allotrope.schema_parser.reference_resolver.download_schema"
    ) as mock_download:
        mock_download.return_value = Path("adm/core/REC/2023/09/fake.schema.json")
        schema_paths = _download_references(references)
        assert schema_paths == {Path("adm/core/REC/2023/09/fake.schema.json")}
        mock_download.assert_called_once_with(
            "http://purl.allotrope.org/json-schemas/adm/core/REC/2023/09/fake.schema",
        )


def test_download_schema() -> None:
    with mock.patch(
        "allotropy.allotrope.schema_parser.reference_resolver.urllib.request.urlretrieve"
    ) as mock_urlretrieve:
        assert download_schema(
            "http://purl.allotrope.org/json-schemas/adm/liquid-chromatography/REC/2023/09/liquid-chromatography.schema"
        ) == Path(
            SCHEMA_DIR_PATH,
            "adm/liquid-chromatography/REC/2023/09/liquid-chromatography.schema.json",
        )
        mock_urlretrieve.assert_not_called()

    with mock.patch(
        "allotropy.allotrope.schema_parser.reference_resolver.urllib.request.urlretrieve"
    ) as mock_urlretrieve:
        assert download_schema(
            "http://purl.allotrope.org/json-schemas/adm/fake/REC/2023/09/fake.schema"
        ) == Path(SCHEMA_DIR_PATH, "adm/fake/REC/2023/09/fake.schema.json")
        mock_urlretrieve.assert_called_once_with(
            "http://purl.allotrope.org/json-schemas/adm/fake/REC/2023/09/fake.schema",
            Path(
                SCHEMA_DIR_PATH,
                "adm/fake/REC/2023/09/fake.schema.json",
            ),
        )
