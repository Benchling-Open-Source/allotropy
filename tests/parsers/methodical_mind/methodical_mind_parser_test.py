import pytest

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents

VENDOR_TYPE = Vendor.METHODICAL_MIND

OUTPUT_FILES = (
    "methodical_test_1.txt",
    "methodical_test_2.txt",
)


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_biorad_bioplex_to_asm_contents(output_file: str) -> None:
    # Validate that file contents are correctly translated to json allotrope model representation
    test_filepath = f"tests/parsers/methodical_mind/testdata/{output_file}"
    expected_filepath = test_filepath.replace(".txt", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict=allotrope_dict, expected_file=expected_filepath)
