import pytest

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents

OUTPUT_FILES = (
    "luminex_xPONENT_example02",
    "luminex_xPONENT_example02_saved",
    "luminex_xPONENT_example03",
)

VENDOR_TYPE = Vendor.LUMINEX_XPONENT


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_luminex_xponent_to_asm(output_file: str) -> None:
    test_filepath = f"tests/parsers/luminex_xponent/testdata/{output_file}.csv"
    expected_filepath = f"tests/parsers/luminex_xponent/testdata/{output_file}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(
        allotrope_dict=allotrope_dict,
        expected_file=expected_filepath,
        write_actual_to_expected_on_fail=False,
    )
