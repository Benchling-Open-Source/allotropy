from datetime import timedelta, timezone, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.timestamp_parser import TimestampParser


def test_timestamp_parser_init_fails_invalid_default_timezone() -> None:
    with pytest.raises(
        AllotropeConversionError, match="Invalid default timezone 'timezone'."
    ):
        TimestampParser("timezone")  # type: ignore[arg-type]


@pytest.mark.short
@pytest.mark.parametrize(
    "time_str,expected",
    [
        ("10-11-08", "2008-10-11T00:00:00+00:00"),
        ("Fri, 11 Nov 2011 03:18:09", "2011-11-11T03:18:09+00:00"),
        ("Fri, 11 Nov 2011 03:18:09 -0400", "2011-11-11T03:18:09-04:00"),
        ("Tue Jun 22 07:46:22 EST 2010", "2010-06-22T07:46:22-05:00"),
        ("Tue Jun 22 07:46:22 EDT 2010", "2010-06-22T07:46:22-04:00"),
        ("Tue Jun 22 07:46:22 GMT 2010", "2010-06-22T07:46:22+00:00"),
    ],
)
def test_timestamp_parser_default_utc(time_str: str, expected: Optional[str]) -> None:
    assert TimestampParser().parse(time_str) == expected


# Similar timezones, but different DST info.
US_PACIFIC = ZoneInfo("US/Pacific")
UTC_MINUS_7 = timezone(timedelta(hours=-7))


@pytest.mark.short
@pytest.mark.parametrize(
    "default_timezone,time_str,expected",
    [
        (US_PACIFIC, "10-11-08", "2008-10-11T00:00:00-07:00"),
        (US_PACIFIC, "Fri, 11 Nov 2011 03:18:09", "2011-11-11T03:18:09-08:00"),
        (US_PACIFIC, "Fri, 11 Jun 2011 03:18:09", "2011-06-11T03:18:09-07:00"),
        (US_PACIFIC, "Fri, 11 Nov 2011 03:18:09 -0400", "2011-11-11T03:18:09-04:00"),
        (US_PACIFIC, "Tue Jun 22 07:46:22 EST 2010", "2010-06-22T07:46:22-05:00"),
        (UTC_MINUS_7, "10-11-08", "2008-10-11T00:00:00-07:00"),
        (UTC_MINUS_7, "Fri, 11 Nov 2011 03:18:09", "2011-11-11T03:18:09-07:00"),
        (UTC_MINUS_7, "Fri, 11 Jun 2011 03:18:09", "2011-06-11T03:18:09-07:00"),
        (UTC_MINUS_7, "Fri, 11 Nov 2011 03:18:09 -0400", "2011-11-11T03:18:09-04:00"),
        (UTC_MINUS_7, "Tue Jun 22 07:46:22 EST 2010", "2010-06-22T07:46:22-05:00"),
    ],
)
def test_timestamp_parser_provided_timezone(
    default_timezone: tzinfo, time_str: str, expected: str
) -> None:
    assert TimestampParser(default_timezone).parse(time_str) == expected


@pytest.mark.short
@pytest.mark.parametrize("time_str", ["blah"])
def test_timestamp_parser_fails_on_invalid_timestamp(time_str: str) -> None:
    parser = TimestampParser()
    with pytest.raises(AllotropeConversionError, match="Could not parse time 'blah'."):
        parser.parse(time_str)


@pytest.mark.short
def test_timestamp_parser_handles_24h_pm() -> None:
    assert (
        TimestampParser().parse("2023-03-16 16:52:37 PM") == "2023-03-16T16:52:37+00:00"
    )
