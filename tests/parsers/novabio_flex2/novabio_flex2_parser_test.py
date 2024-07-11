import pytest

from allotropy.parsers.novabio_flex2.novabio_flex2_parser import NovaBioFlexParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.novabio_flex2.novabio_flex2_data import get_data, get_model


@pytest.mark.short
def test_get_model() -> None:
    parser = NovaBioFlexParser(TimestampParser())
    model = parser._get_model(get_data())

    if model.measurement_aggregate_document:
        model.measurement_aggregate_document.measurement_identifier = ""

    assert model == get_model()
