import pytest

from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

OUTPUT_FILES = (
    "Thermo_NanoDrop_Eight_example01.txt",
    "Thermo_NanoDrop_Eight_example02.txt",
    "Thermo_NanoDrop_Eight_example03.txt",
    "Thermo_NanoDrop_Eight_example04.txt",
)

VENDOR_TYPE = Vendor.THERMO_FISHER_NANODROP_EIGHT
SCHEMA_FILE = "spectrophotometry/BENCHLING/2023/12/spectrophotometry.json"


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_thermo_fisher_nanodrop_eight_to_asm_schema_is_valid(
    output_file: str,
) -> None:
    test_filepath = f"tests/parsers/thermo_fisher_nanodrop_eight/testdata/{output_file}"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, SCHEMA_FILE)


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_thermo_fisher_nanodrop_eight_to_asm_expected_contents(
    output_file: str,
) -> None:
    test_filepath = f"tests/parsers/thermo_fisher_nanodrop_eight/testdata/{output_file}"
    expected_filepath = (
        f"tests/parsers/thermo_fisher_nanodrop_eight/testdata/{output_file}".removesuffix(
            "txt"
        )
        + "json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)
