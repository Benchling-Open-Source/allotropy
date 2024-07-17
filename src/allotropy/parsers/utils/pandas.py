from __future__ import annotations

from collections.abc import Callable, Iterable
import re
from typing import Any, Literal, overload, TypeVar

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.values import (
    assert_not_none,
    str_to_bool,
    try_float_or_nan,
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


T = TypeVar("T", bool, float, int, str)


class SeriesData:
    def __init__(self, series: pd.Series[Any]) -> None:
        self.series = series

    def __getitem__(
        self, type_and_key: tuple[Callable[..., T], str | Iterable[str]]
    ) -> T:
        # Implements index operator
        type_, key = type_and_key
        return assert_not_none(self.get(type_, key), str(key))

    # This overload tells typing that if default is "None" then get might return None
    @overload
    def get(
        self,
        type_: Callable[..., T],
        key: Iterable[str],
        default: Literal[None] = None,
    ) -> T | None:
        ...

    # This overload tells typing that if default matches T, get will return T
    @overload
    def get(self, type_: Callable[..., T], key: Iterable[str], default: T) -> T:
        ...

    def get(
        self,
        type_: Callable[..., T],
        key: Iterable[str],
        default: T | None = None,
    ) -> T | None:
        # Get value from series, if series is an iterable get the first non-null value
        raw_value = (
            self.series.get(key)
            if isinstance(key, str)
            else get_first_not_none(self.series.get, list(key))
        )
        try:
            # bool needs special handling to convert
            if type_ is bool:
                raw_value = "true" if str_to_bool(raw_value) else ""
            value = None if raw_value is None else type_(raw_value)
        except ValueError:
            value = None
        return default if value is None else value

    # TODO(nstender): I can't figure out how to integrate these yet, leaving as "try_..."
    # to signal this.
    def try_non_nan_str_or_none(self, key: str) -> str | None:
        value = self.series.get(key)
        return None if (value is None or pd.isna(value)) else str(value)  # type: ignore[arg-type]

    def try_non_nan_float_or_none(self, key: str) -> float | None:
        return try_non_nan_float_or_none(self.get(str, key))

    def try_float_or_nan(self, key: str) -> JsonFloat:
        return try_float_or_nan(self.get(float, key))
