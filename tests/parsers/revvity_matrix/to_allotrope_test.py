from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.REVVITY_MATRIX


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE
