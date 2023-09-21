import pytest

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parser_factory import _VENDOR_TO_PARSER, get_parser, Vendor


def test_get_parser() -> None:
    for vendor, parser_cls in _VENDOR_TO_PARSER.items():
        assert type(get_parser(vendor)) == parser_cls
        assert type(get_parser(vendor.value)) == parser_cls


def test_get_parser_invalid_vendor() -> None:
    with pytest.raises(AllotropeConversionError, match="unregistered vendor"):
        assert get_parser("fake")


def test_get_parser_invalid_timezone() -> None:
    with pytest.raises(AllotropeConversionError, match="Invalid default timezone"):
        assert get_parser(Vendor.AGILENT_GEN5, default_timezone="blah")  # type: ignore
