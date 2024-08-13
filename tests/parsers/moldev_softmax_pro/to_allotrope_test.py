from pathlib import Path
import re

import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file
from tests.conftest import get_test_cases
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.MOLDEV_SOFTMAX_PRO
TESTDATA = Path(Path(__file__).parent, "testdata")


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


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


@pytest.mark.parametrize(
    "test_file",
    [
        f"{TESTDATA}/errors/fl_kinetic_plates.txt",
        f"{TESTDATA}/errors/lum_spectrum_columns.txt",
    ],
)
def test_unrecognized_read_type(test_file: str) -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Only Endpoint measurements can be processed at this time.",
    ):
        from_file(test_file, VENDOR_TYPE)


@pytest.mark.parametrize("test_filepath", get_test_cases(TESTDATA))
def test_data_source_id_references(
    test_filepath: Path,
) -> None:
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE, CHARDET_ENCODING)
    data_source_ids = []
    if (
        "calculated data aggregate document"
        in allotrope_dict["plate reader aggregate document"]
    ):
        data_source_ids = [
            dsd["data source identifier"]
            for calc_doc in allotrope_dict["plate reader aggregate document"][
                "calculated data aggregate document"
            ]["calculated data document"]
            for dsd in calc_doc["data source aggregate document"][
                "data source document"
            ]
        ]
    measurement_ids = [
        meas_doc["measurement identifier"]
        for spec_doc in allotrope_dict["plate reader aggregate document"][
            "plate reader document"
        ]
        for meas_doc in spec_doc["measurement aggregate document"][
            "measurement document"
        ]
    ]

    for data_source_id in data_source_ids:
        assert (
            data_source_id in measurement_ids
        ), f"data source identifier {data_source_id} is referenced but is not found in any measurement document"
