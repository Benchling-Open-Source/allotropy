from more_itertools import one
import pytest

from allotropy.allotrope.models.adm.cell_counting.benchling._2023._11.cell_counting import (
    Model,
)
from allotropy.constants import CHARDET_ENCODING
from allotropy.parser_factory import Vendor
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_parser import ViCellBluParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.testing.utils import from_file, validate_contents
from tests.parsers.beckman_vi_cell_blu.vi_cell_blu_data import (
    get_data,
    get_filename,
    get_model,
)

OUTPUT_FILES = (
    "Beckman_Vi-Cell-BLU_example01",
    "Beckman_Vi-Cell-BLU_example02",
    "Beckman_Vi-Cell-BLU_example01_utf16",
)

VENDOR_TYPE = Vendor.BECKMAN_VI_CELL_BLU
TEST_DATA_DIR = "tests/parsers/beckman_vi_cell_blu/testdata/"


def _get_test_file_path(output_file: str) -> str:
    return f"{TEST_DATA_DIR}/{output_file}.csv"


def _get_expected_file_path(output_file: str) -> str:
    return f"{TEST_DATA_DIR}/{output_file}.json"


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_vi_cell_blu_to_asm_expected_contents(output_file: str) -> None:
    encoding = CHARDET_ENCODING if "utf16" in output_file else None
    test_filepath = _get_test_file_path(output_file)
    expected_filepath = _get_expected_file_path(output_file)
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE, encoding=encoding)
    validate_contents(allotrope_dict, expected_filepath)


def _clear_measurement_identifier(model: Model) -> None:
    cell_counting_aggregate_document = model.cell_counting_aggregate_document
    assert cell_counting_aggregate_document

    cell_counting_document_item = one(
        cell_counting_aggregate_document.cell_counting_document
    )
    measurement_document = one(
        cell_counting_document_item.measurement_aggregate_document.measurement_document
    )
    measurement_document.measurement_identifier = ""


def test_get_model() -> None:
    parser = ViCellBluParser(TimestampParser())
    result = parser._get_model(get_data(), get_filename())
    _clear_measurement_identifier(result)
    assert result == get_model()
