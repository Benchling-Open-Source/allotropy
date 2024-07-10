from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest


class TestParser(ParserTest):
    VENDOR = Vendor.BIORAD_BIOPLEX
    OVERWRITE_ON_FAILURE = False
