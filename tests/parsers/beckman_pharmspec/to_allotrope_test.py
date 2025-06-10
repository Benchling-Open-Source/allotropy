from pathlib import Path

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import Vendor
from allotropy.testing.utils import from_file
from tests.to_allotrope_test import ParserTest

TESTDATA = Path(Path(__file__).parent, "testdata")


class TestParser(ParserTest):
    VENDOR = Vendor.BECKMAN_PHARMSPEC


def test_to_allotrope_missing_particle_marker() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Unable to find required 'Particle' marker in column 1 of the data file.",
    ):
        from_file(
            f"{TESTDATA}/errors/hiac_missing_particle.xlsx",
            TestParser.VENDOR,
        )


def test_to_allotrope_missing_approver_marker() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Unable to find required 'Approver_' marker in column 0 of the data file.",
    ):
        from_file(
            f"{TESTDATA}/errors/hiac_missing_approver.xlsx",
            TestParser.VENDOR,
        )
