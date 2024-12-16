from pathlib import Path
import re

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.MOLDEV_SOFTMAX_PRO
TESTDATA = Path(Path(__file__).parent, "testdata")


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_handles_header_size_mismatch() -> None:
    with pytest.raises(
        AllotropeConversionError, match="Invalid format - mismatch between # of columns"
    ):
        from_file(
            f"{TESTDATA}/errors/header_size_mismatch.txt",
            VENDOR_TYPE,
        )


def test_handles_unrecognized_read_mode() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match=re.escape(
            "Unrecognized read mode: 'Time Resolved'. Expecting one of ['Absorbance', 'Fluorescence', 'Luminescence']."
        ),
    ):
        from_file(
            f"{TESTDATA}/errors/trf_well_scan_plates.txt",
            VENDOR_TYPE,
        )


def test_missing_kinetic_measurement() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Missing kinetic measurement for well position A1 at 0s.",
    ):
        from_file(f"{TESTDATA}/errors/missing_kinetic_measurement.txt", VENDOR_TYPE)


def test_invalid_measurement_table_dimensions() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Expected 4 rows in measurement table, got 3.",
    ):
        from_file(f"{TESTDATA}/errors/missing_measurement_table_row.txt", VENDOR_TYPE)


@pytest.mark.parametrize(
    "test_file",
    [
        f"{TESTDATA}/errors/lum_spectrum_columns.txt",
    ],
)
def test_unrecognized_read_type(test_file: str) -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Spectrum read type is not currently supported for luminescence plates.",
    ):
        from_file(test_file, VENDOR_TYPE)
