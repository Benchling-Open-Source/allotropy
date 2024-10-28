import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_gen5_image.constants import (
    NO_PLATE_DATA_ERROR,
    UNSUPPORTED_READ_TYPE_ERROR,
)
from allotropy.testing.utils import from_file, get_testdata_dir
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.AGILENT_GEN5_IMAGE
TESTDATA = get_testdata_dir(__file__)


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_to_allotrope_unsupported_kinetic_file() -> None:
    with pytest.raises(AllotropeConversionError, match=UNSUPPORTED_READ_TYPE_ERROR):
        from_file(
            f"{TESTDATA}/errors/kinetics_single_image.txt",
            VENDOR_TYPE,
            encoding=CHARDET_ENCODING,
        )


def test_to_allotrope_invalid_plate_data() -> None:
    with pytest.raises(AllotropeConversionError, match=NO_PLATE_DATA_ERROR):
        from_file(
            f"{TESTDATA}/errors/garbage.txt",
            VENDOR_TYPE,
            encoding=CHARDET_ENCODING,
        )
