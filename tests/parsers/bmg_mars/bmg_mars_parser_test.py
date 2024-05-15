import pytest

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents

OUTPUT_FILES = (
    "16-03-03 13-25-45 472 QC 384 FI",
    "16-03-03 16-54-03 472 ABS 384 QC",
    "16-02-29 14-34-46 Transcreener ADP2 FI",
)

VENDOR_TYPE = Vendor.BMG_MARS
SCHEMA_FILE = "plate-reader/BENCHLING/2023/09/plate-reader.json"


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_bmg_mars_to_asm(output_file: str) -> None:
    test_filepath = f"tests/parsers/bmg_mars/testdata/{output_file}.csv"
    expected_filepath = f"tests/parsers/bmg_mars/testdata/{output_file}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)
