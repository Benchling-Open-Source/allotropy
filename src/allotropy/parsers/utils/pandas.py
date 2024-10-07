from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import Enum
import re
from typing import Any, Literal, overload, TypeVar
import unicodedata

import pandas as pd
from pandas._typing import FilePath, ReadCsvBuffer

from allotropy.allotrope.models.shared.definitions.definitions import (
    InvalidJsonFloat,
)
from allotropy.exceptions import (
    AllotropeConversionError,
    AllotropeParsingError,
)
from allotropy.parsers.utils.iterables import get_first_not_none
from allotropy.parsers.utils.values import (
    assert_is_type,
    assert_not_none,
    str_to_bool,
    try_float_or_none,
)
from allotropy.types import IOType

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


def set_columns(data: pd.DataFrame, column_names: Iterable[str]) -> None:
    cols = list(column_names)
    if data.shape[1] != len(cols):
        msg = f"Invalid format - mismatch between # of columns ({data.shape[1]}) and # of labels ({len(cols)}), column labels: {cols}."
        raise AllotropeConversionError(msg)
    data.columns = pd.Index(cols)


def df_to_series(df: pd.DataFrame, index: int | None = None) -> pd.Series[Any]:
    df = df.dropna(how="all")
    n_rows, _ = df.shape
    if index is None and n_rows != 1:
        msg = "Unable to convert DataFrame to series: data has more than 1 row and no index was provided."
        raise AllotropeConversionError(msg)
    index = index or 0
    if index >= n_rows:
        msg = f"Index {index} is greater than the number of rows in dataframe {n_rows}."
        raise AllotropeConversionError(msg)
    return pd.Series(df.iloc[index], index=df.columns)


def df_to_series_data(df: pd.DataFrame, index: int | None = None) -> SeriesData:
    df.columns = df.columns.astype(str).str.strip()
    return SeriesData(df_to_series(df, index))


def assert_df_column(df: pd.DataFrame, column: str) -> pd.Series[Any]:
    df_column = df.get(column)
    if df_column is None:
        msg = f"Unable to find column '{column}'."
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


def parse_header_row(df: pd.DataFrame) -> pd.DataFrame:
    # Set the first row of a dataframe as the columns. This is useful when the dataframe has already been
    # parsed (e.g. when splitting a dataframe into two parts), and so the header/index_col arguments cannot
    # be used to set the columns/index at read time.
    df.columns = pd.Index(
        assert_not_empty_df(df, "Cannot set parse header row for empty dataframe.")
        .astype(str)
        .iloc[0]
    )
    df.columns = df.astype(str).columns.str.strip()
    return df[1:]


def split_header_and_data(
    df: pd.DataFrame, should_split_on_row: Callable[[pd.Series[Any]], bool]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    for idx, row in df.iterrows():
        if should_split_on_row(row):
            header_end = int(str(idx))
            return df[:header_end], df[header_end + 1 :]

    msg = f"Unable to split header and data from dataframe: {df}"
    raise AllotropeConversionError(msg)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(
        columns=lambda col: unicodedata.normalize("NFKC", col)
        if isinstance(col, str)
        else col
    )


def read_csv(
    # types for filepath_or_buffer match those in pd.read_csv()
    filepath_or_buffer: FilePath | ReadCsvBuffer[bytes] | ReadCsvBuffer[str],
    **kwargs: Any,
) -> pd.DataFrame:
    """Wrap pd.read_csv() and raise AllotropeParsingError for failures.

    pd.read_csv() can return a DataFrame or TextFileReader. The latter is intentionally not supported."""
    try:
        df_or_reader = pd.read_csv(filepath_or_buffer, **kwargs)
    except Exception as e:
        msg = f"Error calling pd.read_csv(): {e}"
        raise AllotropeParsingError(msg) from e
    return _normalize_columns(
        assert_is_type(
            df_or_reader,
            pd.DataFrame,
            "pd.read_csv() returned a TextFileReader, which is not supported.",
        )
    )


def read_excel(
    # io is untyped in pd.read_excel(), but this seems reasonable.
    io: str | IOType,
    **kwargs: Any,
) -> pd.DataFrame:
    """Wrap pd.read_excel() and raise AllotropeParsingError for failures.

    pd.read_excel() can return a DataFrame or a dictionary of DataFrames. The latter is intentionally not supported."""
    try:
        df_or_dict = pd.read_excel(io, **kwargs)
    except Exception as e:
        msg = f"Error calling pd.read_excel(): {e}"
        raise AllotropeParsingError(msg) from e
    return _normalize_columns(
        assert_is_type(df_or_dict, pd.DataFrame, "Expected a single-sheet Excel file.")
    )


def read_multisheet_excel(
    io: str | IOType,
    **kwargs: Any,
) -> dict[str, pd.DataFrame]:
    try:
        df_or_dict = pd.read_excel(io, sheet_name=None, **kwargs)
    except Exception as e:
        msg = f"Error calling pd.read_excel(): {e}"
        raise AllotropeParsingError(msg) from e
    sheets: dict[str, pd.DataFrame] = assert_is_type(
        df_or_dict, dict, "Expected a multi-sheet Excel file."
    )
    return {
        sheet_name: _normalize_columns(
            assert_is_type(df, pd.DataFrame, "Expected all sheets to yield dataframes.")
        )
        for sheet_name, df in sheets.items()
    }


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

    def has_key(self, key: str) -> bool:
        return key in self.series

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
            if type_ is float and isinstance(raw_value, str) and "%" in raw_value:
                raw_value = raw_value.strip("%")
            convert = try_float_or_none if type_ is float else type_
            # mypy can't figure out that try_float_or_none will only be used when type_ is float.
            value = None if raw_value is None else convert(raw_value)  # type: ignore[operator]
        except ValueError:
            value = None
        return default if value is None else value
