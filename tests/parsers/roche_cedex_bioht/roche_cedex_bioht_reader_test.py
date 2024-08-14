import pytest

from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_reader import (
    RocheCedexBiohtReader,
)
from tests.parsers.roche_cedex_bioht.roche_cedex_bioht_data import (
    get_data_stream,
    get_reader_samples,
    get_reader_title,
)


@pytest.mark.short
def test_data_reader() -> None:
    reader = RocheCedexBiohtReader(get_data_stream())

    assert reader.title_data.series.equals(get_reader_title())
    assert reader.samples_data.equals(get_reader_samples())
