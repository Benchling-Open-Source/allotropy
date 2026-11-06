from allotropy.allotrope.converter import structure, unstructure
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.CFXMAESTRO


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


def test_structure_round_trip_keeps_all_fields() -> None:
    asm = from_file("tests/parsers/cfxmaestro/testdata/example01.csv", VENDOR_TYPE)
    assert unstructure(structure(asm)) == asm
