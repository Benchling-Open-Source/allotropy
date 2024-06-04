from pathlib import Path
from unittest import mock

from allotropy.allotrope.schema_parser.path_util import (
    get_manifest_from_schema_path,
    get_model_class_from_schema,
    get_model_file_from_schema_path,
    get_rel_schema_path,
    get_schema_path_from_manifest,
    get_schema_path_from_reference,
)


def test_get_rel_schem_path() -> None:
    assert get_rel_schema_path(
        Path("/Users/nathan.stender/allotropy/src/allotropy/allotrope/schemas/adm/fluorescence/BENCHLING/2023/09/fluorescence.schema.json"),
    ) == Path("adm/fluorescence/BENCHLING/2023/09/fluorescence.schema.json")


def test_get_manifest_from_schema_path() -> None:
    assert (
        get_manifest_from_schema_path(
            Path("adm/fluorescence/BENCHLING/2023/09/fluorescence.schema.json")
        )
        == "http://purl.allotrope.org/manifests/fluorescence/BENCHLING/2023/09/fluorescence.manifest"
    )


def test_get_schema_path_from_manifest() -> None:
    assert (
        get_schema_path_from_manifest(
            "http://purl.allotrope.org/manifests/fluorescence/BENCHLING/2023/09/fluorescence.manifest"
        )
        == "adm/fluorescence/BENCHLING/2023/09/fluorescence.schema.json"
    )


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


def test_get_model_file_from_schema_path() -> None:
    assert (
        get_model_file_from_schema_path(
            Path("adm/cell-counting/BENCHLING/2023/09/cell-counting.schema.json")
        )
        == "adm/cell_counting/benchling/_2023/_09/cell_counting.py"
    )


def test_get_model_class_from_schema() -> None:
    schema = {
        "$asm.manifest": "http://purl.allotrope.org/manifests/fluorescence/BENCHLING/2023/09/fluorescence.manifest"
    }
    fake_module = mock.MagicMock()
    fake_module.Model = "fake_model"
    with mock.patch(
        "allotropy.allotrope.schema_parser.path_util.importlib.import_module"
    ) as mock_import:
        mock_import.return_value = fake_module
        assert get_model_class_from_schema(schema) == "fake_model"
        mock_import.assert_called_once_with(
            "allotropy.allotrope.models.adm.fluorescence.benchling._2023._09.fluorescence"
        )
