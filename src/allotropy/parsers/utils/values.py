import re
from typing import Optional, TypeVar, Union

import pandas as pd

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


T = TypeVar("T")


def assert_df(
    value: Optional[pd.DataFrame], name: Optional[str] = None, msg: Optional[str] = None
) -> pd.DataFrame:
    if value is None:
        error = msg or f"Expected non-null dataframe{f' for {name}' if name else ''}"
        raise AllotropeConversionError(error)
    return value


def assert_not_none(
    value: Optional[T], name: Optional[str] = None, msg: Optional[str] = None
) -> T:
    if value is None:
        error = msg or f"Expected non-null value{f' for {name}' if name else ''}"
        raise AllotropeConversionError(error)
    return value


def value_or_none(value: str) -> Optional[str]:
    return value.strip() or None
