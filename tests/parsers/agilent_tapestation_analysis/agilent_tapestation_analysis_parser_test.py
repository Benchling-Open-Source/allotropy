import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    NO_SCREEN_TAPE_ID_MATCH,
)
from allotropy.testing.utils import from_file, validate_contents

OUTPUT_FILES = (
    "agilent_tapestation_analysis_example_01.xml",
    "agilent_tapestation_analysis_example_03.xml",
)

VENDOR_TYPE = Vendor.AGILENT_TAPESTATION_ANALYSIS


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_agilent_tapestation_analysis_to_asm_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/agilent_tapestation_analysis/testdata/{output_file}"
    expected_filepath = test_filepath.replace(".xml", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)


def test_parse_agilent_tapestation_analysis_no_screen_tape_match_for_sample() -> None:
    test_filepath = "tests/parsers/agilent_tapestation_analysis/testdata/agilent_tapestation_analysis_example_02.xml"
    with pytest.raises(
        AllotropeConversionError,
        match=NO_SCREEN_TAPE_ID_MATCH.format("01-S025-180717-01-899752"),
    ):
        from_file(test_filepath, VENDOR_TYPE)
