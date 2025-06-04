import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, get_testdata_dir
from tests.to_allotrope_test import ParserTest

TESTDATA = get_testdata_dir(__file__)


class TestParser(ParserTest):
    VENDOR = Vendor.BMG_MARS


def test_to_allotrope_unsupported_kinetic_file() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Unable to parse header data: no key-value pairs found with expected format.",
    ):
        from_file(
            f"{TESTDATA}/errors/file_with_no_delimiter_malformed.csv",
            TestParser.VENDOR,
            encoding=CHARDET_ENCODING,
        )
