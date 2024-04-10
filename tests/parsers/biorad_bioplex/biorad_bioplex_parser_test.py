import re
from xml.etree import ElementTree
import pytest
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor

from tests.parsers.test_utils import from_file, validate_contents

VENDOR_TYPE = Vendor.BIORAD_BIOPLEX

output_files = ("bio-rad_bio-plex_manager_example_01.xml")

#@pytest.mark.parametrize("output_file", output_files)
def test_parse_biorad_bioplex_to_asm_contents() -> None:
    # Validate that file contents are correctly translated to json allotrope model representation
    test_filepath = f"tests/parsers/biorad_bioplex/testdata/bio-rad_bio-plex_manager_example_01.xml"
    expected_filepath = test_filepath.replace(".xml", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE, encoding="UTF-8")
    validate_contents(
        allotrope_dict=allotrope_dict,
        expected_file=expected_filepath,
        write_actual_to_expected_on_fail=True,
    )
