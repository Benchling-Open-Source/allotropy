import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, get_testdata_dir
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.AGILENT_TAPESTATION_ANALYSIS
TESTDATA = get_testdata_dir(__file__)


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_parse_agilent_tapestation_analysis_no_screen_tape_match_for_sample() -> None:
    test_filepath = f"{TESTDATA}/agilent_tapestation_analysis_example_02_error.xml"
    with pytest.raises(
        AllotropeConversionError,
        match="01-S025-180717-01-899752",
    ):
        from_file(test_filepath, VENDOR_TYPE)
