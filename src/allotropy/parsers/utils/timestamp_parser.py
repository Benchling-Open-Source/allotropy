from datetime import timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from dateutil import parser, tz, zoneinfo

from allotropy.exceptions import AllotropeConversionError

TIMEZONE_CODES_MAP = {
    **{code: tz.gettz(code) for code in zoneinfo.get_zonefile_instance().zones.keys()},
    # Add daylight savings time codes for USA
    **{
        "EDT": timezone(timedelta(hours=-4), "EDT"),
        "CDT": timezone(timedelta(hours=-5), "CDT"),
        "MDT": timezone(timedelta(hours=-6), "MDT"),
        "PDT": timezone(timedelta(hours=-7), "PDT"),
    },
    "JST": timezone(timedelta(hours=9), "JST"),
    "CEST": timezone(timedelta(hours=2), "CEST"),
    "PST": timezone(timedelta(hours=-8), "PST"),
}


# TODO: TimestampParser should support localization -- e.g., passing "dayfirst=True" to dateutil.parser.parse.
class TimestampParser:
    default_timezone: tzinfo

    def __init__(self, default_timezone: tzinfo | None = None):
        self.default_timezone = default_timezone or ZoneInfo("UTC")

    def parse(self, time: str) -> str:
        """Parse a string to a datetime, then format as an ISO 8601 string.

        If the parsed datetime doesn't have a timezone, use self.default_timezone.

        :param time: the string to parse
        :raises AllotropeConversionError if time cannot be parsed
        """
        try:
            timestamp = parser.parse(time, tzinfos=TIMEZONE_CODES_MAP, fuzzy=True)
        except ValueError as e:
            msg = f"Could not parse time '{time}'."
            raise AllotropeConversionError(msg) from e
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=self.default_timezone)
        return str(timestamp.isoformat())
