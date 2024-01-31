import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

OUTPUT_FILES = ("luminex_xPONENT_example01",)

VENDOR_TYPE = Vendor.LUMINEX_XPONENT


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_luminex_xponent_to_asm(output_file: str) -> None:
    test_filepath = f"tests/parsers/luminex_xponent/testdata/{output_file}.csv"
    expected_filepath = f"tests/parsers/luminex_xponent/testdata/{output_file}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(
        allotrope_dict,
        "multi-analyte-profiling/BENCHLING/2024/01/multi-analyte-profiling.json",
    )
    validate_contents(
        allotrope_dict,
        expected_filepath,
        identifiers_to_exclude=["analyte identifier", "measurement identifier"],
    )
