import pytest

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents

VENDOR_TYPE = Vendor.MABTECH_APEX


@pytest.mark.mabtech
@pytest.mark.parametrize(
    "output_file",
    ["mabtech_apex_example_single_plate"],
)
def test_parse_mabtech_apex_to_asm_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/mabtech_apex/testdata/{output_file}.xlsx"
    expected_filepath = test_filepath.replace(".xlsx", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)
