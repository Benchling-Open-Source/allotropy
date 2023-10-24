import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

output_files = ("Weyland_Yutani_example01",)

SCHEMA = "fluorescence/BENCHLING/2023/09/fluorescence.json"
TESTDATA = "tests/parsers/example_weyland_yutani/testdata"
VENDOR_TYPE = Vendor.EXAMPLE_WEYLAND_YUTANI


@pytest.mark.parametrize("output_file", output_files)
def test_parse_elmer_envision_to_asm(output_file: str) -> None:
    test_filepath = f"{TESTDATA}/{output_file}.csv"
    expected_filepath = f"{TESTDATA}/{output_file}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, SCHEMA)
    validate_contents(allotrope_dict, expected_filepath)
