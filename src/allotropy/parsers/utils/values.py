from __future__ import annotations

import math
import re
from typing import Any, TypeVar

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
    JsonFloat,
    TQuantityValue,
)
from allotropy.exceptions import AllotropeConversionError

PrimitiveValue = str | int | float


def str_to_bool(value: str) -> bool:
    return value.lower() in ("yes", "y", "true", "t", "1")


def try_int(value: str | None, value_name: str) -> int:
    try:
        return int(assert_not_none(value, value_name))
    except ValueError as e:
        msg = f"Invalid integer string: '{value}'."
        raise AllotropeConversionError(msg) from e


def try_int_or_none(value: str | None) -> int | None:
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


def try_float_or_none(value: str | float | None) -> float | None:
    try:
        return float("" if value is None else value)
    except ValueError:
        return None


def try_nan_float_or_none(value: str | float | None) -> JsonFloat | None:
    float_value = try_float_or_none(value) if isinstance(value, str) else value
    if float_value is None:
        return None
    return InvalidJsonFloat.NaN if math.isnan(float_value) else float_value


def try_non_nan_float_or_none(value: str | float | None) -> float | None:
    float_value = try_float_or_none(value)
    return None if float_value is None or math.isnan(float_value) else float_value


def try_non_nan_float(value: str) -> float:
    float_value = try_non_nan_float_or_none(value)
    if float_value is None:
        msg = f"Invalid non nan float string: '{value}'."
        raise AllotropeConversionError(msg)
    return float_value


def try_int_or_nan(value: str | int | None) -> int | InvalidJsonFloat:
    if isinstance(value, int):
        return value
    float_value = try_non_nan_float_or_none(value)
    return InvalidJsonFloat.NaN if float_value is None else int(float_value)


def try_float_or_nan(value: str | float | None) -> JsonFloat:
    float_value = try_non_nan_float_or_none(value)
    return InvalidJsonFloat.NaN if float_value is None else float_value


def natural_sort_key(key: str) -> list[str]:
    """Returns a sort key that treats numeric substrings as parsed integers for comparison."""
    tokens = [token for token in re.split(r"(\d+)", key) if token]
    return [
        f"{int(token):>10}" if token.isdecimal() else token.lower() for token in tokens
    ]


QuantityType = TypeVar("QuantityType", bound=TQuantityValue)


def quantity_or_none(
    value_cls: type[QuantityType],
    value: JsonFloat | list[JsonFloat] | list[int] | None,
    index: int | None = None,
) -> QuantityType | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value_cls(value=value[assert_not_none(index, msg="Cannot provide list to quantity_or_none without index")])  # type: ignore[call-arg]
    # Typing does not know that all subclasses of TQuantityValue have default value for unit set.
    return value_cls(value=value)  # type: ignore[call-arg]


T = TypeVar("T")


def assert_not_none(
    value: T | None, name: str | None = None, msg: str | None = None
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


def assert_df_column(df: pd.DataFrame, column: str) -> pd.Series[Any]:
    df_column = df.get(column)
    if df_column is None:
        msg = f"Unable to find column '{column}'"
        raise AllotropeConversionError(msg)
    return pd.Series(df_column)


def assert_not_empty_df(df: pd.DataFrame, msg: str) -> pd.DataFrame:
    if df.empty:
        raise AllotropeConversionError(msg)
    return df


def assert_value_from_df(df: pd.DataFrame, key: str) -> Any:
    try:
        return df[key]
    except KeyError as e:
        msg = f"Unable to find key '{key}' in dataframe headers: {df.columns.tolist()}"
        raise AllotropeConversionError(msg) from e


def num_to_chars(n: int) -> str:
    d, m = divmod(n, 26)  # 26 is the number of ASCII letters
    return "" if n < 0 else num_to_chars(d - 1) + chr(m + 65)  # chr(65) = 'A'


def str_or_none(value: Any) -> str | None:
    return None if value is None else str(value)
