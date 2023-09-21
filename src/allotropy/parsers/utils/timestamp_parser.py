

from datetime import datetime, timedelta, timezone
from typing import Optional
from dateutil import parser


class TimestampParser:
    def __init__(self, default_timezone: Optional[timezone] = None):
        self.default_timezone = default_timezone or timezone.utc

        self.tzinfos = {
            "EST": timezone(timedelta(hours=-5), "EST"),
            "EDT": timezone(timedelta(hours=-4), "EDT"),
            "CST": timezone(timedelta(hours=-6), "EST"),
            "MST": timezone(timedelta(hours=-7), "EST"),
            "PDT": timezone(timedelta(hours=-8), "EST"),
        }

    def parse(self, time: Optional[str]) -> Optional[datetime]:
        if not time:
            return None
        try:
            timestamp = parser.parse(time, tzinfos=self.tzinfos)
        except ValueError:
            return None
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=self.default_timezone)
        return timestamp.isoformat()
