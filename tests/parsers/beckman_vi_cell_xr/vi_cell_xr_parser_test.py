import re

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

OUTPUT_FILES = (
    "v2.04/Beckman_Vi-Cell-XR_example03_instrumentOutput.xls",
    "v2.06/Beckman_Vi-Cell-XR_example01_instrumentOutput.xlsx",
    "v2.06/Beckman_Vi-Cell-XR_example04_instrumentOutput.xlsx",
    "v2.06/Beckman_Vi-Cell-XR_example05_instrumentOutput.xlsx",
    "v2.06/Beckman_Vi-Cell-XR_example06_instrumentOutput.xlsx",
    "v2.06/Beckman_Vi-Cell-XR_no_total_cells.xlsx",
    "v2.06/Beckman_Vi-Cell-XR_hiddenRow.xlsx",
    "v2.06/style_fill_error.xlsx",
)

VENDOR_TYPE = Vendor.BECKMAN_VI_CELL_XR


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_vi_cell_xr_to_asm_expected_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/beckman_vi_cell_xr/testdata/{output_file}"
    target_filename = output_file.replace(".xlsx", ".json").replace(".xls", ".json")
    expected_filepath = f"tests/parsers/beckman_vi_cell_xr/testdata/{target_filename}"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)


def test_perse_vi_cell_xr_file_without_required_fields_then_raise() -> None:
    test_filepath = "tests/parsers/beckman_vi_cell_xr/testdata/v2.04/Beckman_Vi-Cell-XR_example02_instrumentOutput.xls"
    expected_regex = re.escape(
        "Expected to find lines with all of these headers: ['Viability (%)', 'Viable cells/ml (x10^6)']."
    )
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        from_file(test_filepath, VENDOR_TYPE)
