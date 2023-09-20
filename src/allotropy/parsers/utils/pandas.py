from typing import Optional

import numpy as np
import pandas as pd

from allotropy.parsers.utils.values import assert_not_none


def get_str_from_series(
    series: pd.Series, key: str, default: Optional[str] = None
) -> Optional[str]:
    value = series.get(key)
    return str(value) if value not in ("", None) else default


def assert_str_from_series(series: pd.Series, key: str) -> str:
    return assert_not_none(get_str_from_series(series, key), key)


def bool_or_none(series: pd.Series, key: str) -> Optional[bool]:
    value = series.get(key)
    if isinstance(value, np.bool_):
        return bool(value)
    return None
