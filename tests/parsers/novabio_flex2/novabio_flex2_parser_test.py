from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.NOVABIO_FLEX2


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE
