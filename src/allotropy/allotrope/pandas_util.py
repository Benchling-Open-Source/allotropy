from typing import Any

import pandas as pd

from allotropy.exceptions import AllotropeConversionError


def read_excel(
    **kwargs: Any,
) -> pd.DataFrame:
    try:
        df_or_dict = pd.read_excel(**kwargs)
    except Exception as e:
        msg = "Error calling pd.read_excel()."
        raise AllotropeConversionError(msg) from e
    if not isinstance(df_or_dict, pd.DataFrame):
        msg = "Expected a single-sheet Excel file."
        raise AllotropeConversionError(msg)
    return df_or_dict
