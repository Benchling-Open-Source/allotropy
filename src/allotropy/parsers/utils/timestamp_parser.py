from datetime import timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from dateutil import parser
import pytz

from allotropy.exceptions import AllotropeConversionError

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

    def __init__(self, default_timezone: tzinfo | None = None):
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
        try:
            timestamp = parser.parse(time, tzinfos=TIMEZONE_CODES_MAP, fuzzy=True)
        except ValueError as e:
            msg = f"Could not parse time '{time}'."
            raise AllotropeConversionError(msg) from e
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=self.default_timezone)
        return str(timestamp.isoformat())


_PARSER = TimestampParser()


def parse_timestamp(time: str) -> str:
    return _PARSER.parse(time)


def set_timestamp_parser(parser: TimestampParser) -> None:
    # NOTE: globals are generally discouraged. However, in the context of the allotropy library, it is
    # expected that set_timestamp_parser will be called once at the code entrypoint in to_allotrope,
    # and then used globally. We are chosing to make the tradeoff of potentially confusing behavior if
    # someone tries to change the timestamp parser while making multiple calls to allotropy in parallel
    # for the simplicity of not having to pass timestamp parser around.
    global _PARSER  # noqa: PLW0603
    _PARSER = parser
