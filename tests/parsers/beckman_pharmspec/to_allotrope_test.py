from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest


class TestParser(ParserTest):
    VENDOR = Vendor.BECKMAN_PHARMSPEC
    OVERWRITE_ON_FAILURE = False
