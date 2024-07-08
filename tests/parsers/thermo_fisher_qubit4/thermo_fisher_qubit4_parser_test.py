import pytest

from allotropy.constants import DEFAULT_ENCODING
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents

OUTPUT_FILES = (
    "thermo_fisher_qubit4_example_1.csv",
    "thermo_fisher_qubit4_example_2.xlsx",
    "thermo_fisher_qubit4_example_3.csv",
    "thermo_fisher_qubit4_example_4.xlsx",
)

TEST_DATA_DIR = "tests/parsers/thermo_fisher_qubit4/testdata"
VENDOR_TYPE = Vendor.THERMO_FISHER_QUBIT4


def _get_test_file_path(output_file: str) -> str:
    return f"{TEST_DATA_DIR}/{output_file}"


def _get_expected_file_path(output_file: str) -> str:
    return f"{TEST_DATA_DIR}/{output_file}".split(".")[0] + ".json"


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_qubit4_to_asm(output_file: str) -> None:
    test_filepath = _get_test_file_path(output_file)
    expected_filepath = _get_expected_file_path(output_file)
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE, encoding=DEFAULT_ENCODING)
    validate_contents(
        allotrope_dict,
        expected_filepath,
        write_actual_to_expected_on_fail=True,
    )
