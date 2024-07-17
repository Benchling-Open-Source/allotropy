from pathlib import Path

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.PERKIN_ELMER_ENVISION
TESTDATA = f"{Path(__file__).parent}/testdata"


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_parse_missing_file() -> None:
    test_filepath = f"{TESTDATA}/PE_Envision_fluorescence_example01.tsv"
    with pytest.raises(
        AllotropeConversionError, match=f"File not found: {test_filepath}"
    ):
        from_file(test_filepath, VENDOR_TYPE)


def test_parse_incorrect_vendor() -> None:
    test_filepath = f"{TESTDATA}/PE_Envision_fluorescence_example01.csv"
    with pytest.raises(AllotropeConversionError, match="No plate data found in file."):
        from_file(test_filepath, Vendor.AGILENT_GEN5)


def test_parse_file_missing_headers() -> None:
    test_filepath = f"{TESTDATA}/example01_missing_header_error.csv"
    # TODO: Handle the underlying error better in src
    with pytest.raises(
        AllotropeConversionError,
        match="Expected non-null value for Basic assay information.",
    ):
        from_file(test_filepath, VENDOR_TYPE)
