import pytest

from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_parser import (
    RocheCedexBiohtParser,
)
from tests.parsers.roche_cedex_bioht.roche_cedex_bioht_data import get_data, get_model


@pytest.mark.short
def test_get_model() -> None:
    model = RocheCedexBiohtParser()._get_mapper().map_model(get_data())
    assert model == get_model()
