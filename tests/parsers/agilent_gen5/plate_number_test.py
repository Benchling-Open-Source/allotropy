from typing import Optional

import pytest

from allotropy.parsers.agilent_gen5.plate_data import PlateNumber


@pytest.mark.parametrize(
    "date_,time_,expected",
    [
        ("1/2/2024", "10:48:38 AM", "2024-01-02T10:48:38"),
        ("1/31/2024", "10:48:38 AM", "2024-01-31T10:48:38"),
        ("2/1/2024", "10:48:38 AM", "2024-02-01T10:48:38"),
        ("1/31/2024", "10:48:38", None),
        ("31/1/2024", "10:48:38", None),
        ("2/1/2024", "10:48:38", None),
        ("2/1/2024", "10:48:38 EST", None),
    ],
)
def test_plate_number_parse_datetime(
    date_: str, time_: str, expected: Optional[str]
) -> None:
    if expected:
        datetime_ = PlateNumber._parse_datetime(date_, time_)
        assert datetime_ == expected
    else:
        expected_error_message = (
            f"time data '{date_} {time_}' does not match format '%m/%d/%Y %I:%M:%S %p'"
        )
        # TODO(brian): should raise AllotropeConversionError
        with pytest.raises(ValueError, match=expected_error_message):
            PlateNumber._parse_datetime(date_, time_)
