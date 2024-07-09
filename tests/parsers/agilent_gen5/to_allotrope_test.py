import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.parsers.agilent_gen5.constants import (
    MULTIPLATE_FILE_ERROR,
    NO_PLATE_DATA_ERROR,
    UNSUPORTED_READ_TYPE_ERROR,
)
from allotropy.testing.utils import (
    from_file,
    validate_contents,
)

VENDOR_TYPE = Vendor.AGILENT_GEN5
SCHEMA_FILE = "ultraviolet-absorbance/BENCHLING/2023/09/ultraviolet-absorbance.json"

# This file was manually changed to use UTF-16 encoding to test encoding code paths. git history doesn't show this.
UTF_16_FILEPATH = (
    "tests/parsers/agilent_gen5/testdata/absorbance/endpoint_stdcurve_multiplate.txt"
)

ABSORBANCE_PATH = "tests/parsers/agilent_gen5/testdata/absorbance"

ABSORBANCE_FILENAMES = [
    "endpoint_pathlength_correct_singleplate",
    "endpoint_stdcurve_singleplate",
    "endpoint_stdcurve_singleplate_2",
    "010307_114129_BNCH654563_stdcurve_singleplate01",
]

FLUORESCENCE_FILENAMES = [
    "endpoint_singleplate_filter_withoutStepLabel_withCalculatedValues",
    "endpoint_singleplate_filter_withoutStepLabel",
    "endpoint_singleplate_filter_withStepLabel_withCalculatedValues",
    "endpoint_singleplate_filter_withStepLabel",
    "endpoint_singleplate_monochromator_withoutStepLabel",
    "endpoint_singleplate",
    "alphalisa_endpoint_singleplate",
    "alphalisa_test_2",
]

LUMINESCENCE_FILENAMES = [
    "endpoint_singleplate_withFilter_withoutStepLabel",
    "endpoint_singleplate_withFilter_withStepLabel",
    "endpoint_singleplate_withoutStepLabel",
    "endpoint_singleplate",
    "luminescence_emission_text_val",
]


@pytest.mark.parametrize("filename", ABSORBANCE_FILENAMES)
def test_to_allotrope_absorbance(filename: str) -> None:
    test_filepath = f"{ABSORBANCE_PATH}/{filename}.txt"
    expected_filepath = f"{ABSORBANCE_PATH}/{filename}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)


def test_to_allotrope_absorbance_no_pm_in_time() -> None:
    test_filepath = (
        f"{ABSORBANCE_PATH}/endpoint_pathlength_correct_singleplate_no_pm_in_time.txt"
    )
    expected_filepath = (
        f"{ABSORBANCE_PATH}/endpoint_pathlength_correct_singleplate.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    allotrope_dict["plate reader aggregate document"]["data system document"][
        "file name"
    ] = "endpoint_pathlength_correct_singleplate.txt"

    validate_contents(allotrope_dict, expected_filepath)


def test_to_allotrope_absorbance_well_plate_id_in_filename() -> None:
    filename = "010307_114129_BNCH654563_stdcurve_singleplate01.txt"
    test_filepath = f"{ABSORBANCE_PATH}/{filename}"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, test_filepath.replace(".txt", ".json"))


def test_to_allotrope_absorbance_with_nan_measurements() -> None:
    test_filepath = f"{ABSORBANCE_PATH}/240411_172731_BNCH2345883_abs450_96well_non_numeric_values.txt"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, test_filepath.replace(".txt", ".json"))


@pytest.mark.parametrize("filename", FLUORESCENCE_FILENAMES)
def test_to_allotrope_fluorescence(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/fluorescence/{filename}.txt"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(
        allotrope_dict,
        test_filepath.replace(".txt", ".json"),
    )


@pytest.mark.parametrize("filename", LUMINESCENCE_FILENAMES)
def test_to_allotrope_luminescence(filename: str) -> None:
    test_filepath = f"tests/parsers/agilent_gen5/testdata/luminescence/{filename}.txt"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, test_filepath.replace(".txt", ".json"))


@pytest.mark.parametrize(
    "filepath",
    [
        f"{ABSORBANCE_PATH}/kinetic_helper_gene_growth_curve.txt",
        f"{ABSORBANCE_PATH}/kinetic_singleplate.txt",
    ],
)
def test_to_allotrope_unsupported_kinetic_file(filepath: str) -> None:
    with pytest.raises(AllotropeConversionError, match=UNSUPORTED_READ_TYPE_ERROR):
        from_file(filepath, VENDOR_TYPE)


def test_to_allotrope_unsupported_spectral_scan_file() -> None:
    filepath = f"{ABSORBANCE_PATH}/240307_114129_BNCH654563_spectralScan_example01.txt"
    with pytest.raises(AllotropeConversionError, match=UNSUPORTED_READ_TYPE_ERROR):
        from_file(filepath, VENDOR_TYPE)


def test_to_allotrope_unsupported_area_scan_file() -> None:
    filepath = f"{ABSORBANCE_PATH}/240307_125255_BNCH786865_areaScan_example01.txt"
    with pytest.raises(AllotropeConversionError, match=UNSUPORTED_READ_TYPE_ERROR):
        from_file(filepath, VENDOR_TYPE)


@pytest.mark.parametrize(
    "filepath",
    [
        UTF_16_FILEPATH,
        "tests/parsers/agilent_gen5/testdata/absorbance/kinetic_multiplate.txt",
        "tests/parsers/agilent_gen5/testdata/fluorescence/endpoint_multiplate.txt",
        "tests/parsers/agilent_gen5/testdata/luminescence/endpoint_multiplate.txt",
    ],
)
def test_to_allotrope_invalid_multiplate_file(filepath: str) -> None:
    encoding = "UTF-16" if filepath == UTF_16_FILEPATH else None
    with pytest.raises(AllotropeConversionError, match=MULTIPLATE_FILE_ERROR):
        from_file(filepath, VENDOR_TYPE, encoding=encoding)


def test_to_allotrope_invalid_plate_data() -> None:
    with pytest.raises(AllotropeConversionError, match=NO_PLATE_DATA_ERROR):
        from_file("tests/parsers/agilent_gen5/testdata/garbage.txt", VENDOR_TYPE)
