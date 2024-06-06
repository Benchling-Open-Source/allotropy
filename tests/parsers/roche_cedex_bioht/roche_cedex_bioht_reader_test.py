import pytest

from tests.parsers.roche_cedex_bioht.roche_cedex_bioht_data import (
    get_reader,
    get_reader_samples,
    get_reader_title,
)


@pytest.mark.short
def test_data_reader() -> None:
    reader = get_reader()

    assert reader.title_data.equals(get_reader_title())
    assert reader.samples_data.equals(get_reader_samples())
