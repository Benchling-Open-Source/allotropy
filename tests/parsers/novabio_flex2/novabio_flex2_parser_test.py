# import pytest

from allotropy.parser_factory import Vendor

# from allotropy.parsers.novabio_flex2.novabio_flex2_parser import NovaBioFlexParser
# from allotropy.parsers.utils.timestamp_parser import TimestampParser
# from tests.parsers.novabio_flex2.novabio_flex2_data import get_data, get_model
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.NOVABIO_FLEX2


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE
    OVERWRITE_ON_FAILURE = True


# TODO: Remove or refactor
# @pytest.mark.short
# def test_get_model() -> None:
#     parser = NovaBioFlexParser(TimestampParser())
#     model = parser._get_model(get_data())

#     if model.measurement_aggregate_document:
#         model.measurement_aggregate_document.measurement_identifier = ""

#     assert model == get_model()
