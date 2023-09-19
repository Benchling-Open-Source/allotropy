import pytest

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

output_files = (
    "v2.04/Beckman_Vi-Cell-XR_example03_instrumentOutput.xls",
    "v2.06/Beckman_Vi-Cell-XR_example01_instrumentOutput.xlsx",
    "v2.06/Beckman_Vi-Cell-XR_example04_instrumentOutput.xlsx",
    "v2.06/Beckman_Vi-Cell-XR_example05_instrumentOutput.xlsx",
    "v2.06/Beckman_Vi-Cell-XR_example06_instrumentOutput.xlsx",
)

VENDOR_TYPE = Vendor.BECKMAN_VI_CELL_XR
SCHEMA_FILE = "cell-counter/BENCHLING/2023/09/cell-counter.json"


@pytest.mark.parametrize("output_file", output_files)
def test_parse_vi_cell_xr_to_asm_schema_is_valid(output_file: str) -> None:
    test_filepath = f"tests/parsers/beckman_vi_cell_xr/testdata/{output_file}"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_schema(allotrope_dict, SCHEMA_FILE)


@pytest.mark.parametrize("output_file", output_files)
def test_parse_vi_cell_xr_to_asm_expected_contents(output_file: str) -> None:
    test_filepath = f"tests/parsers/beckman_vi_cell_xr/testdata/{output_file}"
    target_filename = output_file.replace(".xlsx", ".json").replace(".xls", ".json")
    expected_filepath = f"tests/parsers/beckman_vi_cell_xr/testdata/{target_filename}"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)

    validate_contents(allotrope_dict, expected_filepath)


def test_perse_vi_cell_xr_file_without_required_fields_then_raise() -> None:
    test_filepath = "tests/parsers/beckman_vi_cell_xr/testdata/v2.04/Beckman_Vi-Cell-XR_example02_instrumentOutput.xls"
    with pytest.raises(AllotropeConversionError):
        from_file(test_filepath, VENDOR_TYPE)
