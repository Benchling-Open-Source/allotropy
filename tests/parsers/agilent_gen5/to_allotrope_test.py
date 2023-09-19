import pytest

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

VENDOR_TYPE = Vendor.AGILENT_GEN5


@pytest.mark.parametrize(
    "filename",
    [
        "endpoint_pathlength_correct_singleplate",
        "endpoint_stdcurve_singleplate",
        "endpoint_stdcurve_singleplate_2",
        "endpoint_stdcurve_multiplate",
        "kinetic_helper_gene_growth_curve",
        "kinetic_singleplate",
        "kinetic_multiplate",
    ],
)
def test_to_allotrope_absorbance(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/absorbance/{filename}.txt"
    expected_filepath = (
        f"tests/parsers/agilent_gen5/testdata/absorbance/{filename}.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(
        allotrope_dict,
        "ultraviolet-absorbance/BENCHLING/2023/09/ultraviolet-absorbance.json",
    )
    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.parametrize(
    "filename",
    [
        "endpoint_singleplate",
        "endpoint_multiplate",
    ],
)
def test_to_allotrope_fluorescence(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/fluorescence/{filename}.txt"
    expected_filepath = (
        f"tests/parsers/agilent_gen5/testdata/fluorescence/{filename}.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, "fluorescence/BENCHLING/2023/09/fluorescence.json")
    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.parametrize(
    "filename",
    [
        "endpoint_singleplate",
        "endpoint_multiplate",
    ],
)
def test_to_allotrope_luminescence(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/luminescence/{filename}.txt"
    expected_filepath = (
        f"tests/parsers/agilent_gen5/testdata/luminescence/{filename}.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, "luminescence/BENCHLING/2023/09/luminescence.json")
    validate_contents(allotrope_dict, expected_filepath)


def test_to_allotrope_invalid_plate_data() -> None:
    with pytest.raises(AllotropeConversionError, match="No plate data found in file"):
        from_file("tests/parsers/agilent_gen5/testdata/garbage.txt", VENDOR_TYPE)
