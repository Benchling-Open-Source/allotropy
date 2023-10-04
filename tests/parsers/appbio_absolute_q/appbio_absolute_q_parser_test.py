import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

output_files = (
    "Appbio_AbsoluteQ_example01.csv",
    "Appbio_AbsoluteQ_example02.csv",
    "Appbio_AbsoluteQ_example03.csv",
    "Appbio_AbsoluteQ_example04.csv",
    "Appbio_AbsoluteQ_example05.csv",
)

VENDOR_TYPE = Vendor.APPBIO_ABSOLUTE_Q


@pytest.mark.parametrize("output_file", output_files)
def test_parse_appbio_absolute_q_to_asm_schema(output_file: str) -> None:
    test_filepath = f"tests/parsers/appbio_absolute_q/testdata/{output_file}"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, "pcr/BENCHLING/2023/09/dpcr.json")


@pytest.mark.parametrize("output_file", output_files)
def test_parse_appbio_absolute_q_to_asm_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/appbio_absolute_q/testdata/{output_file}"
    expected_filepath = test_filepath.replace(".csv", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)
