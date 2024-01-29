import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import (
    CALCULATED_DATA_IDENTIFIER,
    DATA_SOURCE_IDENTIFIER,
    from_file,
    MEASUREMENT_IDENTIFIER,
    validate_contents,
    validate_schema,
)

OUTPUT_FILES = (
    "Demo_A260_dsDNA_Data",
    "Demo_A280_Protein",
)

VENDOR_TYPE = Vendor.UNCHAINED_LABS_LUNATIC
SCHEMA_FILE = "plate-reader/BENCHLING/2023/09/plate-reader.json"

IDENTIFIERS_TO_EXCLUDE = [
    CALCULATED_DATA_IDENTIFIER,
    DATA_SOURCE_IDENTIFIER,
    MEASUREMENT_IDENTIFIER,
]


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_cedex_bioht_to_asm(output_file: str) -> None:
    test_filepath = f"tests/parsers/unchained_labs_lunatic/testdata/{output_file}.csv"
    expected_filepath = (
        f"tests/parsers/unchained_labs_lunatic/testdata/{output_file}.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, SCHEMA_FILE)
    validate_contents(allotrope_dict, expected_filepath, IDENTIFIERS_TO_EXCLUDE)
