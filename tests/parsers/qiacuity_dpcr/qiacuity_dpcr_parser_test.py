import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

output_files = ("qiacuity_dpcr_example01.csv", "qiacuity_dpcr_example02.csv")

VENDOR_TYPE = Vendor.QIACUITY_DPCR


@pytest.mark.parametrize("output_file", output_files)
def test_parse_qiacuity_dpcr_to_asm_contents(output_file: str) -> None:
    # Validate that file contents are correctly translated to json allotrope model representation
    test_filepath = f"tests/parsers/qiacuity_dpcr/testdata/{output_file}"
    expected_filepath = test_filepath.replace(".csv", ".json")
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(
        allotrope_dict=allotrope_dict,
        expected_file=expected_filepath,
        write_actual_to_expected_on_fail=False,
    )
