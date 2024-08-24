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
    model = PerkinElmerEnvisionParser(TimestampParser())._get_model(
        get_data(), "file.txt"
    )
    assert model == get_model()
