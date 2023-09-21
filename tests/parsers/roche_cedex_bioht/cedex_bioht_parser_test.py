import pytest

from allotropy.parser_factory import Vendor
from allotropy.parsers.roche_cedex_bioht.cedex_bioht_parser import CedexBiohtParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.roche_cedex_bioht.cedex_bioht_data import get_data, get_model
from tests.parsers.test_utils import from_file, validate_contents, validate_schema

output_files = (
    "cedex_bioht_example01",
    "cedex_bioht_example02",
    "cedex_bioht_example03",
    "cedex_bioht_example04",
)

VENDOR_TYPE = Vendor.ROCHE_CEDEX_BIOHT
SCHEMA_FILE = "cell-culture-analyzer/BENCHLING/2023/09/cell-culture-analyzer.json"


@pytest.mark.parametrize("output_file", output_files)
def test_parse_cedex_bioht_to_asm(output_file: str) -> None:
    test_filepath = f"tests/parsers/roche_cedex_bioht/testdata/{output_file}.txt"
    expected_filepath = f"tests/parsers/roche_cedex_bioht/testdata/{output_file}.json"
    allotrope_dict = from_file(test_filepath, VENDOR_TYPE)
    validate_schema(allotrope_dict, SCHEMA_FILE)
    validate_contents(allotrope_dict, expected_filepath)


@pytest.mark.short
def test_get_model() -> None:
    parser = CedexBiohtParser(TimestampParser())
    model = parser._get_model(get_data())

    if model.measurement_aggregate_document:
        model.measurement_aggregate_document.measurement_identifier = ""

    assert model == get_model()
