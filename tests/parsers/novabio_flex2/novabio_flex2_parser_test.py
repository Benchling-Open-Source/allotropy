import pytest

from allotropy.parser_factory import Vendor
from allotropy.parsers.novabio_flex2.novabio_flex2_parser import NovaBioFlexParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.novabio_flex2.novabio_flex2_data import get_data, get_model
from tests.parsers.test_utils import from_file, validate_contents

OUTPUT_FILES = (
    "SampleResultsDEVICE1232021-02-18_104838",
    "SampleResults2022-06-28_142558",
)

VENDOR_TYPE = Vendor.NOVABIO_FLEX2


@pytest.mark.parametrize("output_file", OUTPUT_FILES)
def test_parse_novabio_flex_to_asm(output_file: str) -> None:
    test_filepath = f"tests/parsers/novabio_flex2/testdata/{output_file}.csv"
    expected_filepath = f"tests/parsers/novabio_flex2/testdata/{output_file}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.short
def test_get_model() -> None:
    parser = NovaBioFlexParser(TimestampParser())
    model = parser._get_model(get_data())

    if model.measurement_aggregate_document:
        model.measurement_aggregate_document.measurement_identifier = ""

    assert model == get_model()
