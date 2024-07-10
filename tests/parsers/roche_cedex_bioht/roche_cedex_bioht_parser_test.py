import pytest

from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_parser import (
    RocheCedexBiohtParser,
)
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.roche_cedex_bioht.roche_cedex_bioht_data import get_data, get_model


@pytest.mark.short
def test_get_model() -> None:
    parser = RocheCedexBiohtParser(TimestampParser())
    model = parser._get_model(get_data())

    if model.measurement_aggregate_document:
        model.measurement_aggregate_document.measurement_identifier = ""

    assert model == get_model()
