from pathlib import Path
from unittest import mock

from allotropy.allotrope.schema_parser.path_util import (
    get_full_schema_path,
    get_manifest_from_schema_path,
    get_model_class_from_schema,
    get_model_file_from_schema_path,
    get_rel_schema_path,
    get_schema_path_from_manifest,
    get_schema_path_from_reference,
    SCHEMA_DIR_PATH,
)

REL_SCHEMA_PATH = Path("adm/fluorescence/BENCHLING/2023/09/fluorescence.schema.json")
MANIFEST = "http://purl.allotrope.org/manifests/fluorescence/BENCHLING/2023/09/fluorescence.manifest"


def test_get_rel_schem_path() -> None:
    assert (
        get_rel_schema_path(Path(SCHEMA_DIR_PATH, REL_SCHEMA_PATH)) == REL_SCHEMA_PATH
    )
    assert get_rel_schema_path(REL_SCHEMA_PATH) == REL_SCHEMA_PATH


def test_get_full_schem_path() -> None:
    assert get_full_schema_path(Path(SCHEMA_DIR_PATH, REL_SCHEMA_PATH)) == Path(
        SCHEMA_DIR_PATH, REL_SCHEMA_PATH
    )
    assert get_full_schema_path(REL_SCHEMA_PATH) == Path(
        SCHEMA_DIR_PATH, REL_SCHEMA_PATH
    )


def test_get_manifest_from_schema_path() -> None:
    assert get_manifest_from_schema_path(REL_SCHEMA_PATH) == MANIFEST


def test_get_schema_path_from_manifest() -> None:
    assert get_schema_path_from_manifest(MANIFEST) == REL_SCHEMA_PATH


def test_get_schema_path_from_reference() -> None:
    assert (
        get_schema_path_from_reference(
            "http://purl.allotrope.org/json-schemas/adm/fluorescence/BENCHLING/2023/09/fluorescence.schema"
        )
        == REL_SCHEMA_PATH
    )


def test_get_model_file_from_schema_path() -> None:
    assert get_model_file_from_schema_path(REL_SCHEMA_PATH) == Path(
        "adm/fluorescence/benchling/_2023/_09/fluorescence.py"
    )


def test_get_model_file_from_schema_path_windows_path() -> None:
    # Replace linux / sep with \\ and test.
    rel_windows_path = Path(str(REL_SCHEMA_PATH).replace("/", "\\"))
    # Have to mock get_rel_schema_path in a linux environment since it will fail combining with windows path.
    with mock.patch(
        "allotropy.allotrope.schema_parser.path_util.get_rel_schema_path"
    ) as mock_get_rel:
        mock_get_rel.return_value = rel_windows_path
        assert get_model_file_from_schema_path(rel_windows_path) == Path(
            "adm/fluorescence/benchling/_2023/_09/fluorescence.py"
        )


def test_get_model_class_from_schema() -> None:
    schema = {"$asm.manifest": MANIFEST}
    fake_module = mock.MagicMock()
    fake_module.Model = "fake_model"
    with mock.patch(
        "allotropy.allotrope.schema_parser.path_util.importlib.import_module"
    ) as mock_import:
        mock_import.return_value = fake_module
        assert get_model_class_from_schema(schema) == "fake_model"
        mock_import.assert_called_with(
            "allotropy.allotrope.models.adm.fluorescence.benchling._2023._09.fluorescence"
        )


def test_get_model_class_from_schema_windows_path() -> None:
    schema = {"$asm.manifest": MANIFEST}
    fake_module = mock.MagicMock()
    fake_module.Model = "fake_model"
    with mock.patch(
        "allotropy.allotrope.schema_parser.path_util.importlib.import_module"
    ) as mock_import, mock.patch(
        "allotropy.allotrope.schema_parser.path_util.get_model_file_from_schema_path"
    ) as mock_get_model_file:
        mock_import.return_value = fake_module
        mock_get_model_file.return_value = Path(
            "adm\\fluorescence\\benchling\\_2023\\_09\\fluorescence.py"
        )
        assert get_model_class_from_schema(schema) == "fake_model"
        mock_import.assert_called_with(
            "allotropy.allotrope.models.adm.fluorescence.benchling._2023._09.fluorescence"
        )
