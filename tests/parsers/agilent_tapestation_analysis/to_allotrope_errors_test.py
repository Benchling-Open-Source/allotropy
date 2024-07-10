import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    NO_SCREEN_TAPE_ID_MATCH,
)
from allotropy.testing.utils import from_file

VENDOR_TYPE = Vendor.AGILENT_TAPESTATION_ANALYSIS


def test_parse_agilent_tapestation_analysis_no_screen_tape_match_for_sample() -> None:
    test_filepath = "tests/parsers/agilent_tapestation_analysis/testdata/agilent_tapestation_analysis_example_02_error.xml"
    with pytest.raises(
        AllotropeConversionError,
        match=NO_SCREEN_TAPE_ID_MATCH.format("01-S025-180717-01-899752"),
    ):
        from_file(test_filepath, VENDOR_TYPE)
