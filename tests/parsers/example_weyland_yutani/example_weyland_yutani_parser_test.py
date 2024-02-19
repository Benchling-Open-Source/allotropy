import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

valid_files = (
    "Weyland_Yutani_simple_correct",
    "Weyland_Yutani_checksum_correct",
)

SCHEMA_FILE = "fluorescence/BENCHLING/2023/09/fluorescence.json"
TESTDATA = "tests/parsers/example_weyland_yutani/testdata"
VENDOR_TYPE = Vendor.EXAMPLE_WEYLAND_YUTANI


@pytest.mark.parametrize("filestem", valid_files)
def test_parse_weyland_yutani_to_asm(filestem: str) -> None:
    test_filepath = f"{TESTDATA}/{filestem}.csv"
    expected_filepath = f"{TESTDATA}/{filestem}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)
