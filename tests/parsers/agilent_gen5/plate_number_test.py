import pytest

from allotropy.parser_factory import get_parser, Vendor
from allotropy.parsers.agilent_gen5.plate_data import PlateNumber

TIMESTAMP_PARSER = get_parser(Vendor.AGILENT_GEN5).timestamp_parser


def test_plate_number_parse_datetime() -> None:
    date_ = "1/2/2024"
    time_ = "10:48:38 AM"
    datetime_ = PlateNumber._parse_datetime(date_, time_, TIMESTAMP_PARSER)
    assert datetime_ == "2024-01-02T10:48:38+00:00"


def test_plate_number_parse_datetime_fails() -> None:
    date_ = "1/2/2024"
    time_ = "10:48:38"
    msg = "time data '1/2/2024 10:48:38' does not match format '%m/%d/%Y %I:%M:%S %p'"
    # TODO: should raise AllotropeConversionError
    with pytest.raises(ValueError, match=msg):
        PlateNumber._parse_datetime(date_, time_, TIMESTAMP_PARSER)
