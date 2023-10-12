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


def assert_int(value: Optional[str], name: Optional[str] = None) -> int:
    return assert_not_none(
        try_int(value),
        name,
        msg=f"Expected int value{f' for {name}' if name else ''}",
    )


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


def assert_not_none(
    value: Optional[T], name: Optional[str] = None, msg: Optional[str] = None
) -> T:
    if value is None:
        error = msg or f"Expected non-null value{f' for {name}' if name else ''}"
        raise AllotropeConversionError(error)
    return value


def value_or_none(value: str) -> Optional[str]:
    return value.strip() or None


def df_to_series(df: pd.DataFrame, msg: str) -> pd.Series:
    n_rows, _ = df.shape
    if n_rows == 1:
        return pd.Series(df.iloc[0], index=df.columns)
    raise AllotropeConversionError(msg)


def assert_not_empty_df(df: pd.DataFrame, msg: str) -> pd.DataFrame:
    if df.empty:
        raise AllotropeConversionError(msg)
    return df


def str_from_series(
    data: pd.Series, key: str, default: Optional[str] = None
) -> Optional[str]:
    value = data.get(key, default)
    return None if value is None else str(value)


def assert_str_from_series(
    series: pd.Series, key: str, msg: Optional[str] = None
) -> str:
    return assert_not_none(str_from_series(series, key), key, msg)


def int_from_series(data: pd.Series, key: str) -> Optional[int]:
    try:
        value = data.get(key)
        return try_int(str(value))
    except Exception as e:
        msg = f"Unable to convert {key} to integer value"
        raise AllotropeConversionError(msg) from e


def assert_int_from_series(data: pd.Series, key: str, msg: Optional[str] = None) -> int:
    return assert_not_none(int_from_series(data, key), key, msg)


def float_from_series(data: pd.Series, key: str) -> Optional[float]:
    try:
        value = data.get(key)
        return try_float(str(value))
    except Exception as e:
        msg = f"Unable to convert {key} to float value"
        raise AllotropeConversionError(msg) from e


def assert_float_from_series(
    data: pd.Series, key: str, msg: Optional[str] = None
) -> float:
    return assert_not_none(float_from_series(data, key), key, msg)


def bool_from_series(data: pd.Series, key: str) -> Optional[bool]:
    try:
        value = data.get(key)
        return None if value is None else bool(value)
    except Exception as e:
        msg = f"Unable to convert {key} to bool value"
        raise AllotropeConversionError(msg) from e
