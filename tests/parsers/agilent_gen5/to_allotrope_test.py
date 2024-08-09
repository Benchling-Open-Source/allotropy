from pathlib import Path

import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_gen5.constants import (
    MULTIPLATE_FILE_ERROR,
    MULTIPLE_READ_MODE_ERROR,
    NO_PLATE_DATA_ERROR,
    UNSUPPORTED_READ_TYPE_ERROR,
)
from allotropy.testing.utils import from_file, validate_contents
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.AGILENT_GEN5
TESTDATA = f"{Path(__file__).parent}/testdata"
ABSORBANCE_PATH = f"{TESTDATA}/absorbance"


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_to_allotrope_absorbance_no_pm_in_time() -> None:
    test_filepath = f"{ABSORBANCE_PATH}/exclude/endpoint_pathlength_correct_singleplate_no_pm_in_time.txt"
    expected_filepath = (
        f"{ABSORBANCE_PATH}/endpoint_pathlength_correct_singleplate.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    allotrope_dict["plate reader aggregate document"]["data system document"][
        "file name"
    ] = "endpoint_pathlength_correct_singleplate.txt"

    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.parametrize(
    "filepath",
    [
        f"{ABSORBANCE_PATH}/exclude/kinetic_helper_gene_growth_curve.txt",
        f"{ABSORBANCE_PATH}/exclude/kinetic_singleplate.txt",
    ],
)
def test_to_allotrope_unsupported_kinetic_file(filepath: str) -> None:
    with pytest.raises(AllotropeConversionError, match=UNSUPPORTED_READ_TYPE_ERROR):
        from_file(filepath, VENDOR_TYPE)


def test_to_allotrope_unsupported_spectral_scan_file() -> None:
    filepath = (
        f"{ABSORBANCE_PATH}/exclude/240307_114129_BNCH654563_spectralScan_example01.txt"
    )
    with pytest.raises(AllotropeConversionError, match=UNSUPPORTED_READ_TYPE_ERROR):
        from_file(filepath, VENDOR_TYPE)


def test_to_allotrope_unsupported_area_scan_file() -> None:
    filepath = (
        f"{ABSORBANCE_PATH}/exclude/240307_125255_BNCH786865_areaScan_example01.txt"
    )
    with pytest.raises(AllotropeConversionError, match=UNSUPPORTED_READ_TYPE_ERROR):
        from_file(filepath, VENDOR_TYPE)


def test_to_allotrope_unsupported_multiple_read_modes() -> None:
    filepath = f"{TESTDATA}/multiple_read_modes_error.txt"
    with pytest.raises(AllotropeConversionError, match=MULTIPLE_READ_MODE_ERROR):
        from_file(filepath, VENDOR_TYPE)


@pytest.mark.parametrize(
    "filepath",
    [
        # NOTE: endpoint_stdcurve_multiplate.txt is a UTF-16 encoded.
        f"{ABSORBANCE_PATH}/exclude/endpoint_stdcurve_multiplate.txt",
        f"{ABSORBANCE_PATH}/exclude/kinetic_multiplate.txt",
        f"{TESTDATA}/fluorescence/exclude/endpoint_multiplate.txt",
        f"{TESTDATA}/luminescence/exclude/endpoint_multiplate.txt",
    ],
)
def test_to_allotrope_invalid_multiplate_file(filepath: str) -> None:
    with pytest.raises(AllotropeConversionError, match=MULTIPLATE_FILE_ERROR):
        from_file(filepath, VENDOR_TYPE, encoding=CHARDET_ENCODING)


def test_to_allotrope_invalid_plate_data() -> None:
    with pytest.raises(AllotropeConversionError, match=NO_PLATE_DATA_ERROR):
        from_file(f"{TESTDATA}/garbage_error.txt", VENDOR_TYPE)


def test_to_allotrope_missing_results() -> None:
    with pytest.raises(AllotropeConversionError):
        from_file(f"{TESTDATA}/missing_results_error.txt", VENDOR_TYPE)
