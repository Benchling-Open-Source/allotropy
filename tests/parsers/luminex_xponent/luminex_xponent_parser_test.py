import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import generate_allotrope_and_validate

OUTPUT_FILES = ("luminex_xPONENT_example01",)

VENDOR_TYPE = Vendor.LUMINEX_XPONENT
SCHEMA_FILE = "multi-analyte-profiling/BENCHLING/2024/01/multi-analyte-profiling.json"


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_luminex_xponent_to_asm(output_file: str) -> None:
    test_filepath = f"tests/parsers/luminex_xponent/testdata/{output_file}.csv"
    expected_filepath = f"tests/parsers/luminex_xponent/testdata/{output_file}.json"
    generate_allotrope_and_validate(
        test_filepath, VENDOR_TYPE, SCHEMA_FILE, expected_filepath
    )
