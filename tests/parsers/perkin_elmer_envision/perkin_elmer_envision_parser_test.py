import pytest

from allotropy.parser_factory import Vendor
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_parser import (
    PerkinElmerEnvisionParser,
)
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from tests.parsers.perkin_elmer_envision.perkin_elmer_envision_data import (
    get_data,
    get_model,
)

VENDOR_TYPE = Vendor.PERKIN_ELMER_ENVISION


@pytest.mark.short
def test_get_model() -> None:
    parser = PerkinElmerEnvisionParser(TimestampParser())
    model = parser._get_model(get_data(), "file.txt")

    # remove all random UUIDs
    if agg_doc := model.plate_reader_aggregate_document:
        for i in range(len(plate_doc := agg_doc.plate_reader_document)):
            for j in range(
                len(
                    measurement_doc := plate_doc[
                        i
                    ].measurement_aggregate_document.measurement_document
                )
            ):
                measurement_doc[j].measurement_identifier = ""

    assert model == get_model()
