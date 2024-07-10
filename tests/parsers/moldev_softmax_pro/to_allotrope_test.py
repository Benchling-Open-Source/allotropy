from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest


class TestParser(ParserTest):
    VENDOR = Vendor.MOLDEV_SOFTMAX_PRO
    OVERWRITE_ON_FAILURE = False
