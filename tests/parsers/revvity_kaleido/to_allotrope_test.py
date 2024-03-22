import pytest

from allotropy.constants import CHARDET_ENCODING
from allotropy.parser_factory import Vendor
from tests.parsers.test_utils import from_file, validate_contents

VENDOR_TYPE = Vendor.REVVITY_KALEIDO


@pytest.mark.parametrize(
    "file_name",
    [
        "absorbance/absorbance_endpoint_single_plate_example_01",
        "fluorescence/fluorescence_endpoint_single_plate_example_01",
        "luminescence/luminescence_endpoint_single_plate_example_01",
    ],
)
def test_to_allotrope(file_name: str) -> None:
    test_file = f"tests/parsers/revvity_kaleido/testdata/{file_name}.csv"
    expected_file = f"tests/parsers/revvity_kaleido/testdata/{file_name}.json"
    allotrope_dict = from_file(test_file, VENDOR_TYPE, CHARDET_ENCODING)
    validate_contents(allotrope_dict, expected_file)
