from pathlib import Path

import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_gen5_image.constants import (
    DEFAULT_EXPORT_FORMAT_ERROR,
    NO_PLATE_DATA_ERROR,
    UNSUPPORTED_READ_TYPE_ERROR,
)
from allotropy.testing.utils import from_file
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.AGILENT_GEN5_IMAGE
TESTDATA = Path(Path(__file__).parent, "testdata")


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_to_allotrope_unsupported_kinetic_file() -> None:
    with pytest.raises(AllotropeConversionError, match=UNSUPPORTED_READ_TYPE_ERROR):
        from_file(
            f"{TESTDATA}/errors/kinetics_single_image.txt",
            VENDOR_TYPE,
            encoding=CHARDET_ENCODING,
        )


def test_to_allotrope_results_in_separate_matrices() -> None:
    with pytest.raises(AllotropeConversionError, match=DEFAULT_EXPORT_FORMAT_ERROR):
        from_file(
            f"{TESTDATA}/errors/image_montage_no_results_table.txt",
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
