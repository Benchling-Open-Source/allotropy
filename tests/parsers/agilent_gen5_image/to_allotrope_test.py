from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest


class TestParser(ParserTest):
    VENDOR = Vendor.AGILENT_GEN5_IMAGE
    OVERWRITE_ON_FAILURE = False
