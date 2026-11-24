import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, get_testdata_dir
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.PERKIN_ELMER_ENVISION
TESTDATA = get_testdata_dir(__file__)


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_parse_file_missing_headers() -> None:
    test_filepath = f"{TESTDATA}/example01_missing_header_error.csv"
    # TODO: Handle the underlying error better in src
    with pytest.raises(
        AllotropeConversionError,
        match="Expected non-null value for Basic assay information.",
    ):
        from_file(test_filepath, VENDOR_TYPE)


def test_plate_type_name_on_every_measurement() -> None:
    # The plate type name comes from the "Plate type" section of the file, so every
    # measurement on the plate should report it, not only the first one.
    test_filepath = f"{TESTDATA}/PE_Envision_fluorescence_example02.csv"
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
    assert len(measurements) == 416
    for measurement in measurements:
        sample_custom_info = measurement["sample document"][
            "custom information document"
        ]
        assert sample_custom_info["Name of the plate type"] == "96 General"
        device_control = measurement["device control aggregate document"][
            "device control document"
        ][0]
        assert "Name of the plate type" not in device_control.get(
            "custom information document", {}
        )
