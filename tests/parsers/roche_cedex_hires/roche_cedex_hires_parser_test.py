import pytest

from allotropy.constants import DEFAULT_ENCODING
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents

OUTPUT_FILES = (
    "roche_cedex_hires_example_1.csv",
    "roche_cedex_hires_example_2.xlsx",
    "roche_cedex_hires_example_3.csv",
    "roche_cedex_hires_example_4.xlsx",
)

TEST_DATA_DIR = "tests/parsers/roche_cedex_hires/testdata"
VENDOR_TYPE = Vendor.ROCHE_CEDEX_HIRES


def _get_test_file_path(output_file: str) -> str:
    return f"{TEST_DATA_DIR}/{output_file}"


def _get_expected_file_path(output_file: str) -> str:
    return f"{TEST_DATA_DIR}/{output_file}".split(".")[0] + ".json"


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_cedex_hires_to_asm(output_file: str) -> None:
    test_filepath = _get_test_file_path(output_file)
    expected_filepath = _get_expected_file_path(output_file)
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE, encoding=DEFAULT_ENCODING)
    validate_contents(
        allotrope_dict,
        expected_filepath,
        write_actual_to_expected_on_fail=True,
    )
