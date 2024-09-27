from pathlib import Path

from allotropy.parser_factory import Vendor
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.THERMO_FISHER_NANODROP_EIGHT
TESTDATA = Path(Path(__file__).parent, "testdata")


class TestParser(ParserTest):
    VENDOR = Vendor.THERMO_FISHER_NANODROP_EIGHT
