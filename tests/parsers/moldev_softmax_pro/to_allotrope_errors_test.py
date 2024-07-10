import re

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file

VENDOR_TYPE = Vendor.MOLDEV_SOFTMAX_PRO


def test_handles_unrecognized_read_mode() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            "Unrecognized read mode: 'Time Resolved'. Only ['Absorbance', 'Fluorescence', 'Luminescence'] are supported."
        ),
    ):
        from_file(
            "tests/parsers/moldev_softmax_pro/testdata/errors/trf_well_scan_plates.txt",
            VENDOR_TYPE,
        )


@pytest.mark.parametrize(
    "test_file",
    [
        "tests/parsers/moldev_softmax_pro/testdata/errors/fl_kinetic_plates.txt",
        "tests/parsers/moldev_softmax_pro/testdata/errors/lum_spectrum_columns.txt",
    ],
)
def test_unrecognized_read_type(test_file: str) -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Only Endpoint measurements can be processed at this time.",
    ):
        from_file(test_file, VENDOR_TYPE)
