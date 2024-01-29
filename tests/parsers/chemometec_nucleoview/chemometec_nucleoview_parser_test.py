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
    "chemometec_nucleoview_example01.csv",
    "chemometec_nucleoview_example02.csv",
    "chemometec_nucleoview_example03.csv",
    "chemometec_nucleoview_example04.csv",
    "chemometec_nucleoview_example05.csv",
    "chemometec_nucleoview_example06.csv",
)

VENDOR_TYPE = Vendor.CHEMOMETEC_NUCLEOVIEW
SCHEMA_FILE = "cell-counting/BENCHLING/2023/11/cell-counting.json"

IDENTIFIERS_TO_EXCLUDE = [
    CALCULATED_DATA_IDENTIFIER,
    DATA_SOURCE_IDENTIFIER,
    MEASUREMENT_IDENTIFIER,
]


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_chemometec_nucleoview_to_asm_schema_is_valid(output_file: str) -> None:
    test_filepath = f"tests/parsers/chemometec_nucleoview/testdata/{output_file}"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, SCHEMA_FILE)


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_chemometec_nucleoview_to_asm_expected_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/chemometec_nucleoview//testdata/{output_file}"
    expected_filepath = (
        f"tests/parsers/chemometec_nucleoview/testdata/{output_file}".removesuffix(
            "csv"
        )
        + "json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath, IDENTIFIERS_TO_EXCLUDE)
