import pytest

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents

VENDOR_TYPE = Vendor.BIORAD_BIOPLEX

OUTPUT_FILES = ("bio-rad_bio-plex_manager_example_01.xml",)


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_biorad_bioplex_to_asm_contents(output_file: str) -> None:
    # Validate that file contents are correctly translated to json allotrope model representation
    test_filepath = f"tests/parsers/biorad_bioplex/testdata/{output_file}"
    expected_filepath = test_filepath.replace(".xml", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE, encoding="UTF-8")
    validate_contents(
        allotrope_dict=allotrope_dict,
        expected_file=expected_filepath,
        write_actual_to_expected_on_fail=False,
    )
