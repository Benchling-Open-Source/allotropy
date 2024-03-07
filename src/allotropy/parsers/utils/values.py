from __future__ import annotations

import math
import re
from typing import Any, Optional, TypeVar, Union

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    JsonFloat,
)
from allotropy.exceptions import AllotropeConversionError

PrimitiveValue = Union[str, int, float]


def try_int(value: Optional[str], value_name: str) -> int:
    try:
        return int(assert_not_none(value, value_name))
    except ValueError as e:
        msg = f"Invalid integer string: '{value}'."
        raise AllotropeConversionError(msg) from e


def try_int_or_none(value: Optional[str]) -> Optional[int]:
    try:
        return int(value or "")
    except ValueError:
        return None


def try_float(value: str, value_name: str) -> float:
    assert_not_none(value, value_name)
    try:
        return float(value)
    except ValueError as e:
        msg = f"Invalid float string: '{value}'."
        raise AllotropeConversionError(msg) from e


def try_non_nan_float(value: str) -> float:
    float_value = try_non_nan_float_or_none(value)
    if float_value is None:
        msg = f"Invalid non nan float string: '{value}'."
        raise AllotropeConversionError(msg)
    return float_value


def try_non_nan_float_or_none(value: Optional[str]) -> Optional[float]:
    float_value = try_float_or_none(value)
    return None if float_value is None or math.isnan(float_value) else float_value


def try_float_or_none(value: Optional[str]) -> Optional[float]:
    try:
        return float("" if value is None else value)
    except ValueError:
        return None


def try_float_or_nan(value: Optional[str]) -> JsonFloat:
    float_value = try_non_nan_float_or_none(value)
    return InvalidJsonFloat.NaN if float_value is None else float_value


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
        error = msg or f"Expected non-null value{f' for {name}' if name else ''}."
        raise AllotropeConversionError(error)
    return value


def df_to_series(
    df: pd.DataFrame,
    msg: str,
) -> pd.Series[Any]:
    n_rows, _ = df.shape
    if n_rows == 1:
        return pd.Series(df.iloc[0], index=df.columns)
    raise AllotropeConversionError(msg)


def assert_not_empty_df(df: pd.DataFrame, msg: str) -> pd.DataFrame:
    if df.empty:
        raise AllotropeConversionError(msg)
    return df


def try_str_from_series_or_default(
    data: pd.Series[Any],
    key: str,
    default: str,
) -> str:
    value = data.get(key)
    return default if value is None else str(value)


def try_str_from_series_or_none(
    data: pd.Series[Any],
    key: str,
) -> Optional[str]:
    value = data.get(key)
    return None if value is None else str(value)


def try_str_from_series(
    series: pd.Series[Any],
    key: str,
    msg: Optional[str] = None,
) -> str:
    return assert_not_none(try_str_from_series_or_none(series, key), key, msg)


def try_int_from_series_or_none(
    data: pd.Series[Any],
    key: str,
) -> Optional[int]:
    try:
        value = data.get(key)
        return try_int(str(value), key)
    except Exception as e:
        msg = f"Unable to convert '{value}' (with key '{key}') to integer value."
        raise AllotropeConversionError(msg) from e


def try_int_from_series(
    data: pd.Series[Any],
    key: str,
    msg: Optional[str] = None,
) -> int:
    return assert_not_none(try_int_from_series_or_none(data, key), key, msg)


def try_float_from_series_or_nan(
    data: pd.Series[Any],
    key: str,
) -> JsonFloat:
    try:
        value = data.get(key)
        return try_float_or_nan(str(value))
    except Exception as e:
        msg = f"Unable to convert '{value}' (with key '{key}') to float value."
        raise AllotropeConversionError(msg) from e


def try_float_from_series_or_none(
    data: pd.Series[Any],
    key: str,
) -> Optional[float]:
    try:
        value = data.get(key)
        return try_float_or_none(str(value))
    except Exception as e:
        msg = f"Unable to convert '{value}' (with key '{key}') to float value."
        raise AllotropeConversionError(msg) from e


def try_float_from_series(
    data: pd.Series[Any],
    key: str,
    msg: Optional[str] = None,
) -> float:
    return assert_not_none(try_float_from_series_or_none(data, key), key, msg)


def try_bool_from_series_or_none(
    data: pd.Series[Any],
    key: str,
) -> Optional[bool]:
    try:
        value = data.get(key)
        return None if value is None else bool(value)
    except Exception as e:
        msg = f"Unable to convert '{value}' (with key '{key}') to boolean value."
        raise AllotropeConversionError(msg) from e


def num_to_chars(n: int) -> str:
    d, m = divmod(n, 26)  # 26 is the number of ASCII letters
    return "" if n < 0 else num_to_chars(d - 1) + chr(m + 65)  # chr(65) = 'A'


def str_or_none(value: Any) -> Optional[str]:
    return None if value is None else str(value)
