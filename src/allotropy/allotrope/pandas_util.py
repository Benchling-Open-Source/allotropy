from typing import Any

import pandas as pd

from allotropy.exceptions import AllotropeConversionError


def read_excel(
    io: Any,
    **kwargs: Any,
) -> pd.DataFrame:
    """Wrap pd.read_excel() and raise AllotropeConversionError for failures."""
    try:
        df_or_dict = pd.read_excel(io, **kwargs)
    except Exception as e:
        msg = f"Error calling pd.read_excel(): {e}"
        raise AllotropeConversionError(msg) from e
    if not isinstance(df_or_dict, pd.DataFrame):
        msg = "Expected a single-sheet Excel file."
        raise AllotropeConversionError(msg)
    return df_or_dict
