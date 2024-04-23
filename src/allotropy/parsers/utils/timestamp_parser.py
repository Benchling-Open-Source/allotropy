from datetime import timedelta, timezone, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo

from dateutil import parser
import pytz

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import assert_not_none

TIMEZONE_CODES_MAP = {
    **{code: pytz.timezone(code) for code in pytz.all_timezones},
    # Add daylight savings time codes for USA
    **{
        "EDT": timezone(timedelta(hours=-4), "EDT"),
        "CDT": timezone(timedelta(hours=-5), "CDT"),
        "MDT": timezone(timedelta(hours=-6), "MDT"),
        "PDT": timezone(timedelta(hours=-7), "PDT"),
    },
}


# TODO: TimestampParser should support localization -- e.g., passing "dayfirst=True" to dateutil.parser.parse.
class TimestampParser:
    default_timezone: tzinfo

    def __init__(self, default_timezone: Optional[tzinfo] = None):
        if default_timezone and not isinstance(default_timezone, tzinfo):
            msg = f"Invalid default timezone '{default_timezone}'."
            raise AllotropeConversionError(msg)
        self.default_timezone = default_timezone or ZoneInfo("UTC")

    def parse(self, time: str) -> str:
        """Parse a string to a datetime, then format as an ISO 8601 string.

        If the parsed datetime doesn't have a timezone, use self.default_timezone.

        :param time: the string to parse
        :raises AllotropeConversionError if time cannot be parsed
        """
        assert_not_none(time, "time")

        try:
            timestamp = parser.parse(time, tzinfos=TIMEZONE_CODES_MAP, fuzzy=True)
        except ValueError as e:
            msg = f"Could not parse time '{time}'."
            raise AllotropeConversionError(msg) from e
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=self.default_timezone)
        return str(timestamp.isoformat())
