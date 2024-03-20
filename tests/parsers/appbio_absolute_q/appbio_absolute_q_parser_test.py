import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

OUTPUT_FILES = (
    "Appbio_AbsoluteQ_example01.csv",
    "Appbio_AbsoluteQ_example02.csv",
    "Appbio_AbsoluteQ_example03.csv",
    "Appbio_AbsoluteQ_example04.csv",
    "Appbio_AbsoluteQ_example05.csv",
)

VENDOR_TYPE = Vendor.APPBIO_ABSOLUTE_Q


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_appbio_absolute_q_to_asm_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/appbio_absolute_q/testdata/{output_file}"
    expected_filepath = test_filepath.replace(".csv", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)
