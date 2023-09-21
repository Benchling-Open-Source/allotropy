from datetime import timedelta, timezone

import pytest

from allotropy.parsers.utils.timestamp_parser import TimestampParser


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
def test_timestamp_parser_default_utc(time_str: str, expected: str) -> None:
    assert TimestampParser().parse(time_str) == expected


@pytest.mark.short
@pytest.mark.parametrize(
    "time_str,expected",
    [
        ("10-11-08", "2008-10-11T00:00:00-07:00"),
        ("Fri, 11 Nov 2011 03:18:09", "2011-11-11T03:18:09-07:00"),
        ("Fri, 11 Nov 2011 03:18:09 -0400", "2011-11-11T03:18:09-04:00"),
        ("Tue Jun 22 07:46:22 EST 2010", "2010-06-22T07:46:22-05:00"),
    ],
)
def test_timestamp_parser_provided_timezone(time_str: str, expected: str) -> None:
    assert TimestampParser(timezone(timedelta(hours=-7))).parse(time_str) == expected


@pytest.mark.short
@pytest.mark.parametrize("time_str", ["blah"])
def test_timestamp_parser_returns_none_on_invalid_timestamp(time_str: str) -> None:
    assert TimestampParser().parse(time_str) is None
