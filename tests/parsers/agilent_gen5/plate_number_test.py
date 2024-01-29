from datetime import timedelta, timezone
from typing import Optional

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import get_parser, Vendor
from allotropy.parsers.agilent_gen5.plate_data import PlateNumber
from allotropy.parsers.utils.timestamp_parser import TimestampParser


def _get_parser(default_timezone: Optional[timezone] = None) -> TimestampParser:
    return get_parser(Vendor.AGILENT_GEN5, default_timezone).timestamp_parser


PARSER_UTC = _get_parser()
PARSER_UTC_MINUS_5 = _get_parser(timezone(timedelta(hours=-5)))


@pytest.mark.parametrize(
    "date_,time_,expected,timestamp_parser",
    [
        ("1/2/2024", "10:48:38 AM", "2024-01-02T10:48:38+00:00", PARSER_UTC),
        ("1/31/2024", "10:48:38 AM", "2024-01-31T10:48:38+00:00", PARSER_UTC),
        ("2/1/2024", "10:48:38 AM", "2024-02-01T10:48:38+00:00", PARSER_UTC),
        ("1/31/2024", "10:48:38", "2024-01-31T10:48:38+00:00", PARSER_UTC),
        ("31/1/2024", "10:48:38", "2024-01-31T10:48:38+00:00", PARSER_UTC),
        ("2/1/2024", "10:48:38", "2024-02-01T10:48:38+00:00", PARSER_UTC),
        ("2/1/2024", "10:48:38 EST", "2024-02-01T10:48:38-05:00", PARSER_UTC),
        ("mydate", "mytime", None, PARSER_UTC),
        ("1/2/2024", "10:48:38 AM", "2024-01-02T10:48:38-05:00", PARSER_UTC_MINUS_5),
        ("1/31/2024", "10:48:38 AM", "2024-01-31T10:48:38-05:00", PARSER_UTC_MINUS_5),
        ("2/1/2024", "10:48:38 AM", "2024-02-01T10:48:38-05:00", PARSER_UTC_MINUS_5),
        ("1/31/2024", "10:48:38", "2024-01-31T10:48:38-05:00", PARSER_UTC_MINUS_5),
        ("31/1/2024", "10:48:38", "2024-01-31T10:48:38-05:00", PARSER_UTC_MINUS_5),
        ("2/1/2024", "10:48:38", "2024-02-01T10:48:38-05:00", PARSER_UTC_MINUS_5),
        ("2/1/2024", "10:48:38 EST", "2024-02-01T10:48:38-05:00", PARSER_UTC_MINUS_5),
        ("mydate", "mytime", None, PARSER_UTC),
        ("mydate", "mytime", None, PARSER_UTC_MINUS_5),
    ],
)
def test_plate_number_parse_datetime(
    date_: str, time_: str, expected: Optional[str], timestamp_parser: TimestampParser
) -> None:
    if expected:
        datetime_ = PlateNumber._parse_datetime(date_, time_, timestamp_parser)
        assert datetime_ == expected
    else:
        expected_error_message = f"Could not parse time '{date_} {time_}'"
        with pytest.raises(AllotropeConversionError, match=expected_error_message):
            PlateNumber._parse_datetime(date_, time_, PARSER_UTC)
