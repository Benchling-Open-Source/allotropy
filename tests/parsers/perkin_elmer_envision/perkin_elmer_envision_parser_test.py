from allotropy.parser_factory import Vendor
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_parser import (
    PerkinElmerEnvisionParser,
)
from tests.parsers.perkin_elmer_envision.perkin_elmer_envision_data import (
    get_data,
    get_model,
)

VENDOR_TYPE = Vendor.PERKIN_ELMER_ENVISION


def test_get_model() -> None:
    assert PerkinElmerEnvisionParser()._get_model(get_data(), "file.txt") == get_model()
