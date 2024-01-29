from typing import Optional

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parser_factory import get_parser, Vendor
from allotropy.parsers.agilent_gen5.plate_data import PlateNumber

TIMESTAMP_PARSER = get_parser(Vendor.AGILENT_GEN5).timestamp_parser


@pytest.mark.parametrize(
    "date_,time_,expected",
    [
        ("1/2/2024", "10:48:38 AM", "2024-01-02T10:48:38+00:00"),
        ("1/31/2024", "10:48:38 AM", "2024-01-31T10:48:38+00:00"),
        ("2/1/2024", "10:48:38 AM", "2024-02-01T10:48:38+00:00"),
        ("1/31/2024", "10:48:38", "2024-01-31T10:48:38+00:00"),
        ("31/1/2024", "10:48:38", "2024-01-31T10:48:38+00:00"),
        ("2/1/2024", "10:48:38", "2024-02-01T10:48:38+00:00"),
        ("2/1/2024", "10:48:38 EST", "2024-02-01T10:48:38-05:00"),
        ("mydate", "mytime", None),
    ],
)
def test_plate_number_parse_datetime(
    date_: str, time_: str, expected: Optional[str]
) -> None:
    if expected:
        datetime_ = PlateNumber._parse_datetime(date_, time_, TIMESTAMP_PARSER)
        assert datetime_ == expected
    else:
        expected_error_message = f"Could not parse time '{date_} {time_}'"
        with pytest.raises(AllotropeConversionError, match=expected_error_message):
            PlateNumber._parse_datetime(date_, time_, TIMESTAMP_PARSER)
