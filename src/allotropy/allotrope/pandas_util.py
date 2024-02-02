from typing import Any, Union

import pandas as pd

from allotropy.exceptions import AllotropeConversionError
from allotropy.types import IOType


def read_excel(
    # io is untyped in pd.read_excel(), but this seems reasonable.
    io: Union[str, IOType],
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
