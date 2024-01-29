import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import get_parser, Vendor
from allotropy.parsers.agilent_gen5.plate_data import PlateNumber

TIMESTAMP_PARSER = get_parser(Vendor.AGILENT_GEN5).timestamp_parser


@pytest.mark.parametrize(
    "date_,time_,expected",
    [
        ("1/2/2024", "10:48:38", "2024-01-02T10:48:38+00:00"),
        ("1/2/2024", "10:48:38 AM", "2024-01-02T10:48:38+00:00"),
    ],
)
def test_plate_number_parse_datetime(date_: str, time_: str, expected: str) -> None:
    datetime_ = PlateNumber._parse_datetime(date_, time_, TIMESTAMP_PARSER)
    assert datetime_ == expected


def test_plate_number_parse_datetime_fails() -> None:
    date_ = "mydate"
    time_ = "mytime"
    msg = "Could not parse time 'mydate mytime'"
    with pytest.raises(AllotropeConversionError, match=msg):
        PlateNumber._parse_datetime(date_, time_, TIMESTAMP_PARSER)
