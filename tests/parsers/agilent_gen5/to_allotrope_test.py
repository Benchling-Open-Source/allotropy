import pytest

from allotropy.allotrope.models.ultraviolet_absorbance_benchling_2023_09_ultraviolet_absorbance import (
    Model,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import (
    from_file,
    generate_allotrope_and_validate,
    model_from_file,
)

VENDOR_TYPE = Vendor.AGILENT_GEN5

ABSORBENCE_FILENAMES = [
    "endpoint_pathlength_correct_singleplate",
    "endpoint_stdcurve_singleplate",
    "endpoint_stdcurve_singleplate_2",
    "endpoint_stdcurve_multiplate",
    "kinetic_helper_gene_growth_curve",
    "kinetic_singleplate",
    "kinetic_multiplate",
]

SCHEMA_FILE = "ultraviolet-absorbance/BENCHLING/2023/09/ultraviolet-absorbance.json"


@pytest.mark.parametrize("filename", ABSORBENCE_FILENAMES)
def test_to_allotrope_absorbance(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/absorbance/{filename}.txt"
    expected_filepath = (
        f"tests/parsers/agilent_gen5/testdata/absorbance/{filename}.json"
    )
    generate_allotrope_and_validate(
        test_filepath, VENDOR_TYPE, SCHEMA_FILE, expected_filepath
    )


def test_to_allotrope_absorbance_no_pm_in_time() -> None:
    test_filepath = "tests/parsers/agilent_gen5/testdata/absorbance/endpoint_pathlength_correct_singleplate_no_pm_in_time.txt"
    expected_filepath = "tests/parsers/agilent_gen5/testdata/absorbance/endpoint_pathlength_correct_singleplate.json"
    generate_allotrope_and_validate(
        test_filepath, VENDOR_TYPE, SCHEMA_FILE, expected_filepath
    )


@pytest.mark.parametrize("filename", ABSORBENCE_FILENAMES)
def test_model_from_file_absorbance(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/absorbance/{filename}.txt"
    allotrope_model = model_from_file(test_filepath, VENDOR_TYPE)
    assert isinstance(allotrope_model, Model)
    assert (
        allotrope_model.manifest
        == "http://purl.allotrope.org/manifests/ultraviolet-absorbance/BENCHLING/2023/09/ultraviolet-absorbance.manifest"
    )


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
    schema_file = "fluorescence/BENCHLING/2023/09/fluorescence.json"
    generate_allotrope_and_validate(
        test_filepath, VENDOR_TYPE, schema_file, expected_filepath
    )


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
    schema_file = "luminescence/BENCHLING/2023/09/luminescence.json"
    generate_allotrope_and_validate(
        test_filepath, VENDOR_TYPE, schema_file, expected_filepath
    )


def test_to_allotrope_invalid_plate_data() -> None:
    with pytest.raises(AllotropeConversionError, match="No plate data found in file."):
        from_file("tests/parsers/agilent_gen5/testdata/garbage.txt", VENDOR_TYPE)
