import pytest

# from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents

OUTPUT_FILES = (
    "nexcelom_matrix_1.xlsx",
)

VENDOR_TYPE = Vendor.NEXCELOM_MATRIX


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_nexcelom_matrix_to_asm_expected_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/nexcelom_matrix/testdata/{output_file}"
    target_filename = output_file.replace(".xlsx", ".json").replace(".xls", ".json")
    expected_filepath = f"tests/parsers/nexcelom_matrix/testdata/{target_filename}"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)

# TODO Need more tests
# def test_parse_nexcelom_matrix_file_without_required_fields_then_raise() -> None:
#     test_filepath = "tests/parsers/nexcelom_matrix/testdata/NONE_GIVEN.xlsx"
#     expected_regex = re.escape(
#         "Expected to find lines with all of these headers: ['Viability', 'Live Cells/mL']."
#     )
#     with pytest.raises(AllotropeConversionError, match=expected_regex):
#         from_file(test_filepath, VENDOR_TYPE)
