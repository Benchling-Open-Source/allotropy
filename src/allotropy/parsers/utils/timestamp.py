from datetime import datetime, timezone
from typing import Optional


# TODO(nstender): accept tzinfo into parser to determine timezone of machine.
def get_timestamp(
    time: Optional[str], fmt: str, tzinfo: Optional[timezone] = None
) -> Optional[datetime]:
    try:
        return datetime.strptime(time or "", fmt).replace(tzinfo=tzinfo or timezone.utc)
    except ValueError:
        return None
