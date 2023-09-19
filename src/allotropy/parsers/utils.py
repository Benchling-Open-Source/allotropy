from datetime import datetime, timezone
import re
from typing import Optional, TypeVar, Union

from allotropy.allotrope.allotrope import AllotropeConversionError

PrimitiveValue = Union[str, int, float]


def try_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value or "")
    except ValueError:
        return None


def try_float(value: Optional[str]) -> Optional[float]:
    try:
        return float(value or "")
    except ValueError:
        return None


def natural_sort_key(key: str) -> list[str]:
    """Returns a sort key that treats numeric substrings as parsed integers for comparison."""
    tokens = [token for token in re.split(r"(\d+)", key) if token]
    return [
        f"{int(token):>10}" if token.isdecimal() else token.lower() for token in tokens
    ]


T = TypeVar("T", bound=PrimitiveValue)


def assert_not_none(value: Optional[T], name: str) -> T:
    if value is None:
        error = f"Expected non-null value for {name}"
        raise AllotropeConversionError(error)
    return value


def value_or_none(value: str) -> Optional[str]:
    return value.strip() or None


# TODO(nstender): accept tzinfo into parser to determine timezone of machine.
def get_timestamp(
    time: Optional[str], fmt: str, tzinfo: Optional[timezone] = None
) -> Optional[datetime]:
    try:
        return datetime.strptime(time or "", fmt).replace(tzinfo=tzinfo or timezone.utc)
    except ValueError:
        return None
