from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import Enum
import re
from typing import Any, Literal, overload, TypeVar

import pandas as pd

from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.values import (
    assert_not_none,
    str_to_bool,
)

MapType = TypeVar("MapType")


def map_rows(
    data_frame: pd.DataFrame, func: Callable[[SeriesData], MapType]
) -> list[MapType]:
    def run_with_data(series: pd.Series[str]) -> MapType:
        return func(SeriesData(series))

    # pandas can't find a matching overload for this, but it works and returns the correct type...
    return list(data_frame.apply(run_with_data, axis="columns"))  # type: ignore[call-overload]


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
# Need to use this instead of type[T] to get mypy to realize primitive can be called to return T
Type_ = Callable[..., T]
KeyOrKeys = Iterable[str]
TypeAndKey = tuple[Type_[T], KeyOrKeys]
TypeAndKeyAndMsg = tuple[Type_[T], KeyOrKeys, str]
ValidateRaw = Callable[[Any], bool] | None


class SeriesData:
    class ValidateRawMode(Enum):
        # Return None for key is raw value is None or np.isna
        NOT_NAN = "NOT_NAN"

    NOT_NAN = ValidateRawMode.NOT_NAN

    @staticmethod
    def _validate_raw(v: Any, mode: ValidateRawMode | None) -> Any:
        if mode is SeriesData.ValidateRawMode.NOT_NAN:
            return None if (v is None or pd.isna(v)) else v
        return v

    def __init__(self, series: pd.Series[Any]) -> None:
        self.series = series

    def __getitem__(self, type_and_key: TypeAndKey[T] | TypeAndKeyAndMsg[T]) -> T:
        """
        Get a value of the specified type with the specified key, raising an error if the
        key is not found, or if the value cannot be converted to the type.
        If a third argument is provided, it is an error message to provide if they key is not found.

        value: float = series_data[float, key]
        value: str = series_data[str, key, f"Failed to find {key} in my data"]

        Parameters:
        type (str, int, float, bool): The datatype to return.
        key (str | Iterable[str]): The key (or iterable of keys) to use to lookup.
        msg (str | None): The message to give as an error if lookup or conversion fails.

        Returns:
        type: A value of the type provided.

        Raises
        AllotropeConversionError: If the lookup or conversion to type fails.
        """
        if len(type_and_key) == 2:  # noqa: PLR2004
            type_, key = type_and_key
            msg = None
        elif len(type_and_key) == 3:  # noqa: PLR2004
            type_, key, msg = type_and_key
        return assert_not_none(self.get(type_, key), str(key), msg=msg)

    # This overload tells typing that if default is "None" then get might return None
    @overload
    def get(
        self,
        type_: Type_[T],
        key: KeyOrKeys,
        default: Literal[None] = None,
        validate: ValidateRawMode | None = None,
    ) -> T | None:
        ...

    # This overload tells typing that if default matches T, get will return T
    @overload
    def get(
        self,
        type_: Type_[float],
        key: KeyOrKeys,
        default: InvalidJsonFloat,
        validate: ValidateRawMode | None = None,
    ) -> float | InvalidJsonFloat:
        ...

    # This overload tells typing that if default matches T, get will return T
    @overload
    def get(
        self,
        type_: Type_[T],
        key: KeyOrKeys,
        default: T,
        validate: ValidateRawMode | None = None,
    ) -> T:
        ...

    def get(
        self,
        type_: Type_[T],
        key: KeyOrKeys,
        default: T | InvalidJsonFloat | None = None,
        validate: ValidateRawMode | None = None,
    ) -> T | InvalidJsonFloat | None:
        """
        Get a value of the specified type with the specified key, returning a default value if the
        key is not found, or if the value cannot be converted to the type.
        If validate is provided, it will be used to validate the raw value from the series, returning None
        if the value fails validation.

        Parameters:
        type (str, int, float, bool): The datatype to return.
        key (str | Iterable[str]): The key (or iterable of keys) to use to lookup.
        default (type | InvalidJsonFloat | None): The value to return if lookup or conversion fails (default=None).
        validate (ValidateRawMode): The method to use for validating raw value. Defaults to (value is not None).

        Returns:
        type: A value of the type provided or default value.
        """
        if not isinstance(key, str):
            return get_first_not_none(
                lambda k: self.get(type_, k, validate=validate), key
            )
        raw_value = self._validate_raw(self.series.get(key), validate)
        try:
            # bool needs special handling to convert
            if type_ is bool:
                raw_value = (
                    None
                    if raw_value is None
                    else ("true" if str_to_bool(str(raw_value)) else "")
                )
            value = None if raw_value is None else type_(raw_value)
        except ValueError:
            value = None
        return default if value is None else value
