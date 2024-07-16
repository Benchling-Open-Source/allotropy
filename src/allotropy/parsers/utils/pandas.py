from __future__ import annotations

import re
from typing import Any

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.values import (
    assert_not_none,
    str_to_bool,
    try_float_or_nan,
    try_float_or_none,
    try_int,
    try_non_nan_float_or_none,
)


def rm_df_columns(data: pd.DataFrame, pattern: str) -> pd.DataFrame:
    return data.drop(
        columns=[column for column in data.columns if re.match(pattern, column)]
    )


def df_to_series(
    df: pd.DataFrame, msg: str, index: int | None = None
) -> pd.Series[Any]:
    n_rows, _ = df.shape
    if index is None and n_rows == 1:
        index = 0
    if index is None or index >= n_rows:
        raise AllotropeConversionError(msg)
    return pd.Series(df.iloc[index], index=df.columns)


def df_to_series_data(df: pd.DataFrame, msg: str) -> SeriesData:
    return SeriesData(df_to_series(df, msg))


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


class SeriesData:
    def __init__(self, series: pd.Series[Any]) -> None:
        self.series = series

    def try_str_or_default(self, key: str, default: str) -> str:
        value = self.series.get(key)
        return default if value is None else str(value)

    def try_str_or_none(self, key: str) -> str | None:
        value = self.series.get(key)
        return None if value is None else str(value)

    def try_str(self, key: str, msg: str | None = None) -> str:
        return assert_not_none(self.try_str_or_none(key), key, msg)

    def try_non_nan_str_or_none(self, key: str) -> str | None:
        value = self.series.get(key)
        return None if (value is None or pd.isna(value)) else str(value)  # type: ignore[arg-type]

    def try_str_multikey_or_none(
        self,
        keys: list[str],
    ) -> str | None:
        return get_first_not_none(self.try_str_or_none, keys)

    def try_str_multikey(
        self,
        keys: list[str],
        msg: str | None = None,
    ) -> str:
        return assert_not_none(self.try_str_multikey_or_none(keys), msg=msg)

    def try_int_or_none(self, key: str) -> int | None:
        value = self.try_str_or_none(key)
        try:
            return try_int(value, key)
        except Exception as e:
            msg = f"Unable to convert '{value}' (with key '{key}') to integer value."
            raise AllotropeConversionError(msg) from e

    def try_int(self, key: str, msg: str | None = None) -> int:
        return assert_not_none(self.try_int_or_none(key), key, msg)

    def try_float_or_none(self, key: str) -> float | None:
        value = self.try_str_or_none(key)
        try:
            return try_float_or_none(str(value))
        except Exception as e:
            msg = f"Unable to convert '{value}' (with key '{key}') to float value."
            raise AllotropeConversionError(msg) from e

    def try_float(self, key: str, msg: str | None = None) -> float:
        return assert_not_none(self.try_float_or_none(key), key, msg)

    def try_non_nan_float_or_none(self, key: str) -> float | None:
        value = self.try_str_or_none(key)
        try:
            return try_non_nan_float_or_none(str(value))
        except Exception as e:
            msg = f"Unable to convert '{value}' (with key '{key}') to float value."
            raise AllotropeConversionError(msg) from e

    def try_float_or_nan(self, key: str) -> JsonFloat:
        value = self.try_str_or_none(key)
        try:
            return try_float_or_nan(str(value))
        except Exception as e:
            msg = f"Unable to convert '{value}' (with key '{key}') to float value."
            raise AllotropeConversionError(msg) from e

    def try_bool_or_none(self, key: str) -> bool | None:
        value = self.try_str_or_none(key)
        try:
            return None if value is None else str_to_bool(str(value))
        except Exception as e:
            msg = f"Unable to convert '{value}' (with key '{key}') to boolean value."
            raise AllotropeConversionError(msg) from e

    def try_bool(self, key: str, msg: str | None = None) -> float:
        return assert_not_none(self.try_bool_or_none(key), key, msg)
