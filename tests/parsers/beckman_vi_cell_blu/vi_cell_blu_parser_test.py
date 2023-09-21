import pytest

from allotropy.parser_factory import Vendor
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_parser import ViCellBluParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.beckman_vi_cell_blu.vi_cell_blu_data import (
    get_data,
    get_filename,
    get_model,
)
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

output_files = (
    "Beckman_Vi-Cell-BLU_example01",
    "Beckman_Vi-Cell-BLU_example02",
)

VENDOR_TYPE = Vendor.BECKMAN_VI_CELL_BLU
SCHEMA_FILE = "cell-counter/BENCHLING/2023/09/cell-counter.json"


@pytest.mark.parametrize("output_file", output_files)
def test_parse_vi_cell_blu_to_asm_schema_is_valid(output_file: str) -> None:
    test_filepath = f"tests/parsers/beckman_vi_cell_blu//testdata/{output_file}.csv"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, SCHEMA_FILE)


@pytest.mark.parametrize("output_file", output_files)
def test_parse_vi_cell_blu_to_asm_expected_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/beckman_vi_cell_blu//testdata/{output_file}.csv"
    expected_filepath = f"tests/parsers/beckman_vi_cell_blu/testdata/{output_file}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)


def test_get_model() -> None:
    parser = ViCellBluParser(TimestampParser())
    result = parser._get_model(get_data(), get_filename())

    cell_counting_document_item = (
        result.cell_counting_aggregate_document.cell_counting_document[0]
    )
    measurement_document_item = (
        cell_counting_document_item.measurement_aggregate_document.measurement_document[
            0
        ]
    )
    measurement_document_item.measurement_identifier = ""

    assert result == get_model()
