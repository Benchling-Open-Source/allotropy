from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest
import pytest
from allotropy.exceptions import AllotropeConversionError
from allotropy.testing.utils import get_testdata_dir
from allotropy.to_allotrope import allotrope_from_file

TESTDATA = get_testdata_dir(__file__)


class TestParser(ParserTest):
    VENDOR = Vendor.NOVABIO_FLEX2

    def test_missing_date_time_column(self) -> None:
        """Test that an error is raised when 'Date & Time' column is missing."""
        filepath = f"{TESTDATA}/exclude/missing_date_time.csv"
        with pytest.raises(AllotropeConversionError, match="Missing 'Date & Time' column in the CSV file. This is required for NovaBio Flex2 files."):
            allotrope_from_file(filepath, vendor_type=self.VENDOR)
