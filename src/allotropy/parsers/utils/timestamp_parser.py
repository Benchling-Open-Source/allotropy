from datetime import timedelta, timezone, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo

from dateutil import parser
import pytz

from allotropy.allotrope.allotrope import AllotropeConversionError

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


class TimestampParser:
    default_timezone: tzinfo

    def __init__(self, default_timezone: Optional[tzinfo] = None):
        if default_timezone and not isinstance(default_timezone, tzinfo):
            msg = f"Invalid default timezone '{default_timezone}'"
            raise AllotropeConversionError(msg)
        self.default_timezone = default_timezone or ZoneInfo("UTC")

    def parse(self, time: Optional[str]) -> Optional[str]:
        if not time:
            return None
        try:
            timestamp = parser.parse(time, tzinfos=TIMEZONE_CODES_MAP, fuzzy=True)
        except ValueError:
            return None
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=self.default_timezone)
        return str(timestamp.isoformat())
