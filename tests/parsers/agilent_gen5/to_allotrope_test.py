from pathlib import Path

import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_gen5.constants import (
    MULTIPLATE_FILE_ERROR,
    NO_MEASUREMENTS_ERROR,
    NO_PLATE_DATA_ERROR,
    UNSUPPORTED_READ_TYPE_ERROR,
)
from allotropy.testing.utils import from_file, get_testdata_dir, validate_contents
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.AGILENT_GEN5
TESTDATA = get_testdata_dir(__file__)
ABSORBANCE_PATH = Path(TESTDATA, "absorbance")


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


@pytest.mark.long
def test_to_allotrope_absorbance_no_pm_in_time() -> None:
    test_filename = "endpoint_pathlength_correct_singleplate_no_pm_in_time"
    test_filepath = f"{ABSORBANCE_PATH}/exclude/{test_filename}.txt"
    expected_filepath = f"{ABSORBANCE_PATH}/{test_filename}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    allotrope_dict["plate reader aggregate document"]["data system document"][
        "file name"
    ] = f"{test_filename}.txt"

    validate_contents(allotrope_dict, expected_filepath)


def test_to_allotrope_unsupported_area_scan_file() -> None:
    filepath = (
        f"{ABSORBANCE_PATH}/exclude/240307_125255_BNCH786865_areaScan_example01.txt"
    )
    with pytest.raises(AllotropeConversionError, match=UNSUPPORTED_READ_TYPE_ERROR):
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
    with pytest.raises(AllotropeConversionError, match=NO_MEASUREMENTS_ERROR):
        from_file(f"{TESTDATA}/missing_results_error.txt", VENDOR_TYPE)


def test_to_allotrope_no_measurements_error() -> None:
    with pytest.raises(AllotropeConversionError, match=NO_MEASUREMENTS_ERROR):
        from_file(
            f"{TESTDATA}/calculated_data_with_no_measurements_error.txt", VENDOR_TYPE
        )


def test_to_allotrope_header_custom_info_on_every_measurement() -> None:
    # Reading Type and Plate Number come from the file header, so every measurement
    # in the plate should report them, not only the first one.
    test_filepath = (
        f"{ABSORBANCE_PATH}/010307_114129_BNCH654563_stdcurve_singleplate01.txt"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    plate_documents = allotrope_dict["plate reader aggregate document"][
        "plate reader document"
    ]
    measurements = [
        measurement
        for plate_document in plate_documents
        for measurement in plate_document["measurement aggregate document"][
            "measurement document"
        ]
    ]
    assert len(measurements) == 96
    for measurement in measurements:
        device_control = measurement["device control aggregate document"][
            "device control document"
        ][0]
        sample_custom_info = measurement["sample document"][
            "custom information document"
        ]
        assert device_control["custom information document"] == {
            "Reading Type": "Manual"
        }
        assert sample_custom_info["Plate Number"] == "Plate 1"
