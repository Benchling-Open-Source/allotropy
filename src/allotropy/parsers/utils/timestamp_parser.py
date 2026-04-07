from datetime import timedelta, timezone, tzinfo
import re
from zoneinfo import ZoneInfo

from babel import Locale
from babel.dates import get_date_format
from dateutil import parser, tz, zoneinfo

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.locale_context import get_current_locale

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


def _should_use_day_first(time_str: str, locale_str: str | None) -> bool:
    """Determine if dateutil.parser should use dayfirst=True for parsing.

    Year-first formats (ISO 8601: YYYY-MM-DD) always use month before day.
    For other formats, use Babel's CLDR data to check the locale's standard date format.

    Args:
        time_str: The timestamp string to parse
        locale_str: Locale string like "en_US", "de_DE", or None

    Returns:
        True if parser should use dayfirst=True (day before month)
        False if parser should use dayfirst=False (month before day, or year-first ISO format)
    """
    # ISO 8601 year-first format (YYYY-MM-DD or YYYY/MM/DD) is always month-before-day
    if re.match(r"^\d{4}[-/.]", time_str):
        return False

    # Use locale data for non-ISO formats
    if not locale_str:
        return False

    try:
        locale = Locale.parse(locale_str)
        date_format = get_date_format("short", locale=locale)
        pattern = date_format.pattern

        # Check if day appears before month in the locale's date pattern
        d_pos = pattern.find("d")
        m_pos = pattern.find("M")

        if d_pos >= 0 and m_pos >= 0:
            return d_pos < m_pos

        return False
    except Exception:
        return False


class TimestampParser:
    default_timezone: tzinfo

    def __init__(self, default_timezone: tzinfo | None = None):
        self.default_timezone = default_timezone or ZoneInfo("UTC")

    def parse(self, time: str) -> str:
        """Parse a string to a datetime, then format as an ISO 8601 string.

        If the parsed datetime doesn't have a timezone, use self.default_timezone.
        Date format (day-first vs month-first) is determined by locale from the current
        context using Babel CLDR data, except for ISO 8601 year-first formats which are
        always YYYY-MM-DD.

        :param time: the string to parse
        :raises AllotropeConversionError if time cannot be parsed
        """
        # Get locale from context (set via set_locale_context in to_allotrope.py)
        locale = get_current_locale()
        dayfirst = _should_use_day_first(time, locale)

        try:
            timestamp = parser.parse(
                time, tzinfos=TIMEZONE_CODES_MAP, fuzzy=True, dayfirst=dayfirst
            )
        except ValueError as e:
            msg = f"Could not parse time '{time}'."
            raise AllotropeConversionError(msg) from e
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=self.default_timezone)
        return str(timestamp.isoformat())
