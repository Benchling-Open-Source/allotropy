from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.THERMO_FISHER_NANODROP_ONE


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE
