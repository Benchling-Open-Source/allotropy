import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_gen5_image.constants import (
    DEFAULT_EXPORT_FORMAT_ERROR,
    NO_PLATE_DATA_ERROR,
    UNSUPORTED_READ_TYPE_ERROR,
)
from allotropy.testing.utils import (
    from_file,
    validate_contents,
)

VENDOR_TYPE = Vendor.AGILENT_GEN5_IMAGE

TESTDATA_PATH = "tests/parsers/agilent_gen5_image/testdata"

GEN5_IMAGE_FILENAMES = [
    "96-Well Trevigen CometAssayCometChip Imaging and Analysis Sample File 23Nov15",
    "HeLa 96well Colony 11pt Doxorubicin UprBF_TAB",
    "Cell_Count_DAPI_GFP",
]


@pytest.mark.parametrize("filename", GEN5_IMAGE_FILENAMES)
def test_to_allotrope_absorbance(filename: str) -> None:
    test_filepath = f"{TESTDATA_PATH}/{filename}.txt"
    expected_filepath = f"{TESTDATA_PATH}/{filename}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE, encoding=CHARDET_ENCODING)
    validate_contents(allotrope_dict, expected_filepath)


def test_to_allotrope_unsupported_kinetic_file() -> None:
    with pytest.raises(AllotropeConversionError, match=UNSUPORTED_READ_TYPE_ERROR):
        from_file(
            f"{TESTDATA_PATH}/kinetics_single_image.txt",
            VENDOR_TYPE,
            encoding=CHARDET_ENCODING,
        )


def test_to_allotrope_results_in_separate_matrices() -> None:
    with pytest.raises(AllotropeConversionError, match=DEFAULT_EXPORT_FORMAT_ERROR):
        from_file(
            f"{TESTDATA_PATH}/image_montage_no_results_table.txt",
            VENDOR_TYPE,
            encoding=CHARDET_ENCODING,
        )


def test_to_allotrope_invalid_plate_data() -> None:
    with pytest.raises(AllotropeConversionError, match=NO_PLATE_DATA_ERROR):
        from_file(
            f"{TESTDATA_PATH}/garbage.txt", VENDOR_TYPE, encoding=CHARDET_ENCODING
        )
