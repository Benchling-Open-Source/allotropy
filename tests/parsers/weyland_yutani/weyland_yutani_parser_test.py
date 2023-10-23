import pytest

from allotropy.parser_factory import Vendor
from allotropy.parsers.weyland_yutani.weyland_yutani_parser import (
    WeylandYutaniParser,
)
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

output_files = (
    "Weyland_Yutani_example01",
)

VENDOR_TYPE = Vendor.WEYLAND_YUTANI


@pytest.mark.parametrize("output_file", output_files)
def test_parse_elmer_envision_to_asm(output_file: str) -> None:
    test_filepath = f"tests/parsers/weyland_yutani/testdata/{output_file}.csv"
    expected_filepath = (
        f"tests/parsers/weyland_yutani/testdata/{output_file}.json"
    )
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, "fluorescence/BENCHLING/2023/09/fluorescence.json")
    validate_contents(allotrope_dict, expected_filepath)
