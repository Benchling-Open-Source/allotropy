import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

OUTPUT_FILES = (
    "Demo_A260_dsDNA_Data",
    "Demo_A280_Protein",
)

VENDOR_TYPE = Vendor.UNCHAINED_LABS_LUNATIC
SCHEMA_FILE = "plate-reader/BENCHLING/2023/09/plate-reader.json"


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_cedex_bioht_to_asm(output_file: str) -> None:
    test_filepath = f"tests/parsers/unchained_labs_lunatic/testdata/{output_file}.csv"
    expected_filepath = (
        f"tests/parsers/unchained_labs_lunatic/testdata/{output_file}.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)
