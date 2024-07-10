from pathlib import Path

import pytest

from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file
from tests.conftest import get_test_cases
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.THERMO_FISHER_NANODROP_EIGHT
TESTDATA = Path(Path(__file__).parent, "testdata")


class TestParser(ParserTest):
    VENDOR = Vendor.THERMO_FISHER_NANODROP_EIGHT


@pytest.mark.parametrize("test_filepath", get_test_cases(TESTDATA))
def test_parse_thermo_fisher_nanodrop_eight_data_source_ids(
    test_filepath: Path,
) -> None:
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    data_source_ids = [
        dsd["data source identifier"]
        for calc_doc in allotrope_dict["spectrophotometry aggregate document"][
            "calculated data aggregate document"
        ]["calculated data document"]
        for dsd in calc_doc["data source aggregate document"]["data source document"]
    ]
    measurement_ids = [
        meas_doc["measurement identifier"]
        for spec_doc in allotrope_dict["spectrophotometry aggregate document"][
            "spectrophotometry document"
        ]
        for meas_doc in spec_doc["measurement aggregate document"][
            "measurement document"
        ]
    ]

    for data_source_id in data_source_ids:
        assert (
            data_source_id in measurement_ids
        ), f"data source identifier {data_source_id} is referenced but is not found in any measurement document"
