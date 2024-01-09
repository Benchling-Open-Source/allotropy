import re

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

VENDOR_TYPE = Vendor.MOLDEV_SOFTMAX_PRO


@pytest.mark.parametrize(
    "file_name",
    [
        "abs_endpoint_plates",
        "MD_SMP_absorbance_endpoint_example01",
        "MD_SMP_absorbance_endpoint_example02",
        "MD_SMP_absorbance_endpoint_example04",
        "MD_SMP_absorbance_endpoint_example05",
        "MD_SMP_fluorescence_endpoint_example07",
        "MD_SMP_fluorescence_endpoint_example06",
        "MD_SMP_luminescence_endpoint_example03",
        "MD_SMP_luminescence_endpoint_example08",
        "MD_SMP_luminescence_endpoint_example09",
    ],
)
def test_to_allotrope(file_name: str) -> None:
    test_file = f"tests/parsers/moldev_softmax_pro/testdata/{file_name}.txt"
    expected_file = f"tests/parsers/moldev_softmax_pro/testdata/{file_name}.json"
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
