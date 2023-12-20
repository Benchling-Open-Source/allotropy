import re

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

VENDOR_TYPE = Vendor.MOLDEV_SOFTMAX_PRO


@pytest.mark.parametrize(
    "test_file,expected_file",
    [
        (
            "tests/parsers/moldev_softmax_pro/testdata/abs_endpoint_plates.txt",
            "tests/parsers/moldev_softmax_pro/testdata/expected_abs_endpoint.json",
        ),
    ],
)
def test_to_allotrope(test_file: str, expected_file: str) -> None:
    allotrope_dict = from_file(test_file, VENDOR_TYPE)
    validate_schema(allotrope_dict, "plate-reader/BENCHLING/2023/09/plate-reader.json")
    validate_contents(allotrope_dict, expected_file)


def test_handles_unrecognized_read_mode() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            "Unrecognized read mode: 'Time Resolved'. Only ['Absorbance', 'Fluorescence', 'Luminescence'] are supported."
        ),
    ):
        from_file(
            "tests/parsers/moldev_softmax_pro/testdata/trf_well_scan_plates.txt",
            VENDOR_TYPE,
        )


@pytest.mark.parametrize(
    "test_file",
    [
        "tests/parsers/moldev_softmax_pro/testdata/fl_kinetic_plates.txt",
        "tests/parsers/moldev_softmax_pro/testdata/lum_spectrum_columns.txt",
    ],
)
def test_unrecognized_read_type(test_file: str) -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Only Endpoint measurements can be processed at this time.",
    ):
        from_file(test_file, VENDOR_TYPE)
