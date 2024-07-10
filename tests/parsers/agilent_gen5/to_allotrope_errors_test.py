import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_gen5.constants import (
    MULTIPLATE_FILE_ERROR,
    NO_PLATE_DATA_ERROR,
    UNSUPORTED_READ_TYPE_ERROR,
)
from allotropy.testing.utils import from_file

VENDOR_TYPE = Vendor.AGILENT_GEN5
TESTDATA_PATH = "tests/parsers/agilent_gen5/testdata/"
ABSORBANCE_PATH = f"{TESTDATA_PATH}/absorbance"


@pytest.mark.parametrize(
    "filepath",
    [
        f"{ABSORBANCE_PATH}/exclude/kinetic_helper_gene_growth_curve.txt",
        f"{ABSORBANCE_PATH}/exclude/kinetic_singleplate.txt",
    ],
)
def test_to_allotrope_unsupported_kinetic_file(filepath: str) -> None:
    with pytest.raises(AllotropeConversionError, match=UNSUPORTED_READ_TYPE_ERROR):
        from_file(filepath, VENDOR_TYPE)


def test_to_allotrope_unsupported_spectral_scan_file() -> None:
    filepath = (
        f"{ABSORBANCE_PATH}/exclude/240307_114129_BNCH654563_spectralScan_example01.txt"
    )
    with pytest.raises(AllotropeConversionError, match=UNSUPORTED_READ_TYPE_ERROR):
        from_file(filepath, VENDOR_TYPE)


def test_to_allotrope_unsupported_area_scan_file() -> None:
    filepath = (
        f"{ABSORBANCE_PATH}/exclude/240307_125255_BNCH786865_areaScan_example01.txt"
    )
    with pytest.raises(AllotropeConversionError, match=UNSUPORTED_READ_TYPE_ERROR):
        from_file(filepath, VENDOR_TYPE)


@pytest.mark.parametrize(
    "filepath",
    [
        # NOTE: endpoint_stdcurve_multiplate.txt is a UTF-16 encoded.
        f"{ABSORBANCE_PATH}/exclude/endpoint_stdcurve_multiplate.txt",
        f"{ABSORBANCE_PATH}/exclude/kinetic_multiplate.txt",
        f"{TESTDATA_PATH}/fluorescence/exclude/endpoint_multiplate.txt",
        f"{TESTDATA_PATH}/luminescence/exclude/endpoint_multiplate.txt",
    ],
)
def test_to_allotrope_invalid_multiplate_file(filepath: str) -> None:
    with pytest.raises(AllotropeConversionError, match=MULTIPLATE_FILE_ERROR):
        from_file(filepath, VENDOR_TYPE, encoding=CHARDET_ENCODING)


def test_to_allotrope_invalid_plate_data() -> None:
    with pytest.raises(AllotropeConversionError, match=NO_PLATE_DATA_ERROR):
        from_file(f"{TESTDATA_PATH}/garbage_error.txt", VENDOR_TYPE)
