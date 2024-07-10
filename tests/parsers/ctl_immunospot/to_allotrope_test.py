import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file, validate_contents


@pytest.mark.parametrize(
    "file_name",
    [
        "ctl_immunospot_example1",
        "ctl_immunospot_example2",
    ],
)
def test_to_allotrope(file_name: str) -> None:
    test_file = f"tests/parsers/ctl_immunospot/testdata/{file_name}.txt"
    expected_file = f"tests/parsers/ctl_immunospot/testdata/{file_name}.json"
    allotrope_dict = from_file(test_file, Vendor.CTL_IMMUNOSPOT, CHARDET_ENCODING)
    validate_contents(allotrope_dict, expected_file)
