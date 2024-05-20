from __future__ import annotations

from typing import Any

import pandas as pd
from pandas._typing import FilePath, ReadCsvBuffer

from allotropy.exceptions import AllotropeConversionError
from allotropy.types import IOType


def read_csv(
    # types for filepath_or_buffer match those in pd.read_csv()
    filepath_or_buffer: FilePath | ReadCsvBuffer[bytes] | ReadCsvBuffer[str],
    **kwargs: Any,
) -> pd.DataFrame:
    """Wrap pd.read_csv() and raise AllotropeConversionError for failures.

    pd.read_csv() can return a DataFrame or TextFileReader. The latter is intentionally not supported."""
    try:
        df_or_reader = pd.read_csv(filepath_or_buffer, **kwargs)
    except Exception as e:
        msg = f"Error calling pd.read_csv(): {e}"
        raise AllotropeConversionError(msg) from e
    return _df_or_bust(
        df_or_reader, "pd.read_csv() returned a TextFileReader, which is not supported."
    )


def read_excel(
    # io is untyped in pd.read_excel(), but this seems reasonable.
    io: str | IOType,
    **kwargs: Any,
) -> pd.DataFrame:
    """Wrap pd.read_excel() and raise AllotropeConversionError for failures.

    pd.read_excel() can return a DataFrame or a dictionary of DataFrames. The latter is intentionally not supported."""
    try:
        df_or_dict = pd.read_excel(io, **kwargs)
    except Exception as e:
        msg = f"Error calling pd.read_excel(): {e}"
        raise AllotropeConversionError(msg) from e
    return _df_or_bust(df_or_dict, "Expected a single-sheet Excel file.")


def _df_or_bust(possible_df: Any, error_message: str) -> pd.DataFrame:
    if isinstance(possible_df, pd.DataFrame):
        return possible_df
    raise AllotropeConversionError(error_message)
