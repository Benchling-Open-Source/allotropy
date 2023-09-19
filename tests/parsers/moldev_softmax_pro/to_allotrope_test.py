import pytest

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

VENDOR_TYPE = Vendor.MOLDEV_SOFTMAX_PRO


@pytest.mark.parametrize(
    "test_file,schema_file,expected_file",
    [
        (
            "tests/parsers/moldev_softmax_pro/testdata/fl_kinetic_plates.txt",
            "fluorescence/BENCHLING/2023/09/fluorescence.json",
            "tests/parsers/moldev_softmax_pro/testdata/expected_fl_kinetic.json",
        ),
        (
            "tests/parsers/moldev_softmax_pro/testdata/lum_spectrum_columns.txt",
            "luminescence/BENCHLING/2023/09/luminescence.json",
            "tests/parsers/moldev_softmax_pro/testdata/expected_lum_spectrum.json",
        ),
        (
            "tests/parsers/moldev_softmax_pro/testdata/abs_endpoint_plates.txt",
            "ultraviolet-absorbance/BENCHLING/2023/09/ultraviolet-absorbance.json",
            "tests/parsers/moldev_softmax_pro/testdata/expected_abs_endpoint.json",
        ),
    ],
)
def test_to_allotrope(test_file: str, schema_file: str, expected_file: str) -> None:
    allotrope_dict = from_file(test_file, VENDOR_TYPE)
    validate_schema(allotrope_dict, schema_file)
    validate_contents(allotrope_dict, expected_file)
    assert (
        len(allotrope_dict["measurement aggregate document"]["measurement document"])
        == 96
    )


def test_handles_unrecognized_read_mode() -> None:
    with pytest.raises(
        AllotropeConversionError, match="unrecognized read mode Time Resolved"
    ):
        from_file(
            "tests/parsers/moldev_softmax_pro/testdata/trf_well_scan_plates.txt",
            VENDOR_TYPE,
        )
