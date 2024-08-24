import pytest

from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_parser import (
    RocheCedexBiohtParser,
)
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.roche_cedex_bioht.roche_cedex_bioht_data import get_data, get_model


def test_get_model() -> None:
    parser = RocheCedexBiohtParser(TimestampParser())
    model = parser._get_mapper().map_model(get_data())
    assert model == get_model()
