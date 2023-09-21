from datetime import timedelta, timezone
from typing import Optional

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
    def __init__(self, default_timezone: Optional[timezone] = None):
        if default_timezone and not isinstance(default_timezone, timezone):
            msg = f"Invalid default timezone '{default_timezone}'"
            raise AllotropeConversionError(msg)
        self.default_timezone = default_timezone or timezone.utc

    def parse(self, time: Optional[str]) -> Optional[str]:
        if not time:
            return None
        try:
            timestamp = parser.parse(time, tzinfos=TIMEZONE_CODES_MAP)
        except ValueError:
            return None
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=self.default_timezone)
        return timestamp.isoformat()
