import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents


OUTPUT_FILES = ("appbio_quantstudio_designandanalysis_QS1_Standard_Curve_example01",)

VENDOR_TYPE = Vendor.APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_appbio_quantstudio_to_asm_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/appbio_quantstudio_designandanalysis/testdata/{output_file}.xlsx"
    expected_filepath = test_filepath.replace(".xlsx", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)
