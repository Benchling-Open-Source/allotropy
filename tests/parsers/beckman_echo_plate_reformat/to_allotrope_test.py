from allotropy.parser_factory import Vendor
from allotropy.testing.utils import get_testdata_dir
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.BECKMAN_ECHO_PLATE_REFORMAT
TESTDATA = get_testdata_dir(__file__)

class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE
